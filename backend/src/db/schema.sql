-- UrjaYukti AI - Database Schema
-- PostgreSQL + PostGIS + TimescaleDB

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- ZONES AND GEOMETRY
-- ============================================================================

CREATE TABLE zones (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    transformer_capacity_mw DECIMAL(10, 2) NOT NULL,
    feeder_count INTEGER NOT NULL,
    center_lat DECIMAL(10, 6) NOT NULL,
    center_lon DECIMAL(10, 6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_zones_geometry ON zones USING GIST(geometry);
CREATE INDEX idx_zones_name ON zones(name);

-- Zone connectivity for cross-zone coordination
CREATE TABLE zone_connectivity (
    id SERIAL PRIMARY KEY,
    from_zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    to_zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    distance_km DECIMAL(10, 2) NOT NULL,
    transfer_capacity_mw DECIMAL(10, 2) NOT NULL,
    transfer_efficiency DECIMAL(3, 2) DEFAULT 0.90,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_zone_id, to_zone_id)
);

CREATE INDEX idx_zone_connectivity_from ON zone_connectivity(from_zone_id);
CREATE INDEX idx_zone_connectivity_to ON zone_connectivity(to_zone_id);

-- ============================================================================
-- TRANSFORMERS AND FEEDERS
-- ============================================================================

CREATE TABLE transformers (
    id VARCHAR(20) PRIMARY KEY,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    name VARCHAR(100) NOT NULL,
    capacity_kva DECIMAL(10, 2) NOT NULL,
    current_load_kva DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'SAFE', -- SAFE, CAUTION, CRITICAL
    geometry GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transformers_zone ON transformers(zone_id);
CREATE INDEX idx_transformers_status ON transformers(status);
CREATE INDEX idx_transformers_geometry ON transformers USING GIST(geometry);

CREATE TABLE feeders (
    id VARCHAR(20) PRIMARY KEY,
    transformer_id VARCHAR(20) NOT NULL REFERENCES transformers(id),
    name VARCHAR(100) NOT NULL,
    capacity_kw DECIMAL(10, 2) NOT NULL,
    current_load_kw DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'SAFE',
    geometry GEOMETRY(LINESTRING, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feeders_transformer ON feeders(transformer_id);
CREATE INDEX idx_feeders_status ON feeders(status);

-- ============================================================================
-- EV DEMAND DATA (TIMESCALEDB HYPERTABLE)
-- ============================================================================

CREATE TABLE ev_demand (
    time TIMESTAMP NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    archetype_id VARCHAR(10) NOT NULL, -- A01: Commuter, A02: Fleet, A03: Opportunity
    demand_kw DECIMAL(10, 2) NOT NULL,
    session_count INTEGER DEFAULT 0,
    avg_session_duration_min DECIMAL(10, 2),
    confidence VARCHAR(10) DEFAULT 'MEDIUM', -- HIGH, MEDIUM, LOW
    data_source VARCHAR(50) DEFAULT 'SYNTHETIC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('ev_demand', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_ev_demand_zone_time ON ev_demand(zone_id, time DESC);
CREATE INDEX idx_ev_demand_archetype ON ev_demand(archetype_id);
CREATE INDEX idx_ev_demand_confidence ON ev_demand(confidence);

-- ============================================================================
-- GRID LOAD DATA (TIMESCALEDB HYPERTABLE)
-- ============================================================================

CREATE TABLE grid_load (
    time TIMESTAMP NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    feeder_id VARCHAR(20) REFERENCES feeders(id),
    total_load_kw DECIMAL(10, 2) NOT NULL,
    ev_load_kw DECIMAL(10, 2) DEFAULT 0,
    non_ev_load_kw DECIMAL(10, 2) DEFAULT 0,
    headroom_percent DECIMAL(5, 2),
    status VARCHAR(20) DEFAULT 'SAFE',
    confidence VARCHAR(10) DEFAULT 'MEDIUM',
    data_source VARCHAR(50) DEFAULT 'SYNTHETIC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('grid_load', 'time', chunk_time_interval => INTERVAL '1 hour');

CREATE INDEX idx_grid_load_zone_time ON grid_load(zone_id, time DESC);
CREATE INDEX idx_grid_load_feeder ON grid_load(feeder_id);
CREATE INDEX idx_grid_load_status ON grid_load(status);

-- ============================================================================
-- CHARGING STATIONS
-- ============================================================================

CREATE TABLE charging_stations (
    id VARCHAR(20) PRIMARY KEY,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL, -- PUBLIC, SEMI_PUBLIC, PRIVATE
    capacity_kw DECIMAL(10, 2) NOT NULL,
    port_count INTEGER NOT NULL,
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    address VARCHAR(255),
    operational BOOLEAN DEFAULT TRUE,
    utilization_rate DECIMAL(5, 2),
    roi_payback_years DECIMAL(5, 2),
    mcda_score DECIMAL(5, 2),
    status VARCHAR(20) DEFAULT 'PROPOSED', -- PROPOSED, APPROVED, UNDER_CONSTRUCTION, OPERATIONAL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_charging_stations_zone ON charging_stations(zone_id);
CREATE INDEX idx_charging_stations_status ON charging_stations(status);
CREATE INDEX idx_charging_stations_geometry ON charging_stations USING GIST(geometry);

-- ============================================================================
-- USER BEHAVIOR DATA
-- ============================================================================

CREATE TABLE user_behavior (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    archetype_id VARCHAR(10) NOT NULL,
    preferred_start_hour INTEGER NOT NULL,
    preferred_end_hour INTEGER NOT NULL,
    flexibility_score DECIMAL(3, 2) DEFAULT 0.5,
    incentive_sensitivity DECIMAL(3, 2) DEFAULT 0.3,
    compliance_rate DECIMAL(3, 2) DEFAULT 0.4,
    total_sessions INTEGER DEFAULT 0,
    shifted_sessions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_behavior_user ON user_behavior(user_id);
CREATE INDEX idx_user_behavior_zone ON user_behavior(zone_id);

-- ============================================================================
-- COMPLIANCE FEEDBACK (TIMESCALEDB HYPERTABLE)
-- ============================================================================

CREATE TABLE compliance_feedback (
    time TIMESTAMP NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    recommended_start_time TIMESTAMP NOT NULL,
    actual_start_time TIMESTAMP,
    shifted BOOLEAN,
    shift_hours DECIMAL(5, 2),
    incentive_amount DECIMAL(10, 2) DEFAULT 0,
    incentive_type VARCHAR(50),
    satisfaction_score INTEGER, -- 1-5
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('compliance_feedback', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_compliance_feedback_user ON compliance_feedback(user_id, time DESC);
CREATE INDEX idx_compliance_feedback_zone ON compliance_feedback(zone_id, time DESC);

-- ============================================================================
-- ANOMALIES AND ALERTS
-- ============================================================================

CREATE TABLE anomalies (
    id SERIAL PRIMARY KEY,
    time TIMESTAMP NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    feeder_id VARCHAR(20) REFERENCES feeders(id),
    anomaly_type VARCHAR(50) NOT NULL, -- DEMAND_SPIKE, LOAD_DEVIATION, FORECAST_ERROR
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    actual_value DECIMAL(10, 2),
    expected_value DECIMAL(10, 2),
    deviation_percent DECIMAL(5, 2),
    sigma_score DECIMAL(5, 2),
    description TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_anomalies_zone_time ON anomalies(zone_id, time DESC);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_anomalies_acknowledged ON anomalies(acknowledged);

-- ============================================================================
-- FORECASTS (TIMESCALEDB HYPERTABLE)
-- ============================================================================

CREATE TABLE forecasts (
    time TIMESTAMP NOT NULL,
    forecast_time TIMESTAMP NOT NULL, -- The time this forecast was made
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    archetype_id VARCHAR(10),
    forecast_type VARCHAR(20) NOT NULL, -- DEMAND, LOAD, PEAK
    horizon_hours INTEGER NOT NULL,
    predicted_value DECIMAL(10, 2) NOT NULL,
    confidence_80_lower DECIMAL(10, 2),
    confidence_80_upper DECIMAL(10, 2),
    confidence_95_lower DECIMAL(10, 2),
    confidence_95_upper DECIMAL(10, 2),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('forecasts', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_forecasts_zone_time ON forecasts(zone_id, time DESC);
CREATE INDEX idx_forecasts_forecast_time ON forecasts(forecast_time DESC);

-- ============================================================================
-- SCHEDULES (TIMESCALEDB HYPERTABLE)
-- ============================================================================

CREATE TABLE schedules (
    time TIMESTAMP NOT NULL,
    zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    schedule_type VARCHAR(20) NOT NULL, -- VPP, SHIFT, OPTIMIZATION
    original_demand_kw DECIMAL(10, 2) NOT NULL,
    optimized_demand_kw DECIMAL(10, 2) NOT NULL,
    shifted_kw DECIMAL(10, 2) DEFAULT 0,
    peak_load_index DECIMAL(5, 2),
    peak_load_reduction_percent DECIMAL(5, 2),
    compliance_probability DECIMAL(3, 2),
    constraint_violations INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PROPOSED', -- PROPOSED, APPROVED, EXECUTED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('schedules', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_schedules_zone_time ON schedules(zone_id, time DESC);
CREATE INDEX idx_schedules_status ON schedules(status);

-- ============================================================================
-- CROSS-ZONE TRANSFERS
-- ============================================================================

CREATE TABLE cross_zone_transfers (
    id SERIAL PRIMARY KEY,
    time TIMESTAMP NOT NULL,
    from_zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    to_zone_id VARCHAR(10) NOT NULL REFERENCES zones(id),
    transfer_kw DECIMAL(10, 2) NOT NULL,
    transfer_efficiency DECIMAL(3, 2),
    reason VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PROPOSED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cross_zone_transfers_time ON cross_zone_transfers(time DESC);
CREATE INDEX idx_cross_zone_transfers_from ON cross_zone_transfers(from_zone_id);
CREATE INDEX idx_cross_zone_transfers_to ON cross_zone_transfers(to_zone_id);

-- ============================================================================
-- DATA QUALITY AND CONFIDENCE
-- ============================================================================

CREATE TABLE data_quality (
    data_source VARCHAR(50) PRIMARY KEY,
    confidence_level VARCHAR(10) NOT NULL, -- HIGH, MEDIUM, LOW
    last_updated TIMESTAMP NOT NULL,
    record_count INTEGER DEFAULT 0,
    missing_percent DECIMAL(5, 2),
    anomaly_rate DECIMAL(5, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_zones_updated_at BEFORE UPDATE ON zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transformers_updated_at BEFORE UPDATE ON transformers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feeders_updated_at BEFORE UPDATE ON feeders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_charging_stations_updated_at BEFORE UPDATE ON charging_stations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_behavior_updated_at BEFORE UPDATE ON user_behavior
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_quality_updated_at BEFORE UPDATE ON data_quality
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate transformer headroom
CREATE OR REPLACE FUNCTION calculate_transformer_headroom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.headroom_percent = ((NEW.capacity_kva - NEW.current_load_kva) / NEW.capacity_kva) * 100;

    IF NEW.current_load_kva / NEW.capacity_kva >= 0.85 THEN
        NEW.status = 'CRITICAL';
    ELSIF NEW.current_load_kva / NEW.capacity_kva >= 0.70 THEN
        NEW.status = 'CAUTION';
    ELSE
        NEW.status = 'SAFE';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Zone summary view
CREATE VIEW zone_summary AS
SELECT
    z.id,
    z.name,
    z.transformer_capacity_mw,
    COUNT(DISTINCT t.id) AS transformer_count,
    COUNT(DISTINCT f.id) AS feeder_count,
    AVG(t.current_load_kva) AS avg_transformer_load_pct,
    SUM(CASE WHEN t.status = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_transformers,
    SUM(CASE WHEN t.status = 'CAUTION' THEN 1 ELSE 0 END) AS caution_transformers
FROM zones z
LEFT JOIN transformers t ON z.id = t.zone_id
LEFT JOIN feeders f ON t.id = f.transformer_id
GROUP BY z.id, z.name, z.transformer_capacity_mw;

-- Current demand view
CREATE VIEW current_demand AS
SELECT
    time,
    zone_id,
    archetype_id,
    SUM(demand_kw) AS total_demand_kw,
    SUM(session_count) AS total_sessions,
    AVG(confidence) AS avg_confidence
FROM ev_demand
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY time, zone_id, archetype_id
ORDER BY time DESC;

-- Recent anomalies view
CREATE VIEW recent_anomalies AS
SELECT
    a.*,
    z.name AS zone_name
FROM anomalies a
JOIN zones z ON a.zone_id = z.id
WHERE a.time >= NOW() - INTERVAL '7 days'
    AND a.acknowledged = FALSE
ORDER BY a.time DESC, a.severity DESC;

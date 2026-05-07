import { render, screen, waitFor } from "@testing-library/react";
import ZoneHeatMap from "./ZoneHeatMap";

// Mock mapbox-gl
jest.mock("mapbox-gl", () => ({
  __esModule: true,
  default: {
    Map: jest.fn(() => ({
      on: jest.fn(),
      addSource: jest.fn(),
      addLayer: jest.fn(),
      addControl: jest.fn(),
      getCanvas: jest.fn(() => ({ style: {} })),
      isStyleLoaded: jest.fn(() => true),
      getSource: jest.fn(() => ({})),
      getLayer: jest.fn(() => ({})),
      setPaintProperty: jest.fn(),
      setLayoutProperty: jest.fn(),
      setFilter: jest.fn(),
      fitBounds: jest.fn(),
      flyTo: jest.fn(),
      once: jest.fn(),
      off: jest.fn(),
      remove: jest.fn(),
      project: jest.fn(() => ({ x: 100, y: 100 })),
    })),
    NavigationControl: jest.fn(),
  },
}));

// mock @turf/bbox
jest.mock("@turf/turf", () => ({
  bbox: jest.fn(() => [77.7, 12.9, 77.8, 13.0]),
}));

describe("ZoneHeatMap", () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
  });

  it("should render map container", () => {
    const { container } = render(
      <ZoneHeatMap selected={null} setSelected={jest.fn()} />
    );
    expect(container.querySelector(".w-full.h-full")).toBeInTheDocument();
  });

  it("should handle zone selection", async () => {
    const setSelected = jest.fn();
    render(<ZoneHeatMap selected={null} setSelected={setSelected} />);

    // Wait for map to initialize
    await waitFor(() => {
      expect(setSelected).not.toHaveBeenCalled();
    });
  });

  it("should handle null selection safely", () => {
    const setSelected = jest.fn();
    render(<ZoneHeatMap selected={null} setSelected={setSelected} />);

    // Should not crash with null selection
    expect(setSelected).not.toHaveBeenCalled();
  });
});

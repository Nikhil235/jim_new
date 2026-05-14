/*
 * Latency Monitor Header
 * =======================
 * Monitor and log order execution latencies.
 * Critical for backtesting and live trading analysis.
 */

#ifndef MEDALLION_LATENCY_MONITOR_H
#define MEDALLION_LATENCY_MONITOR_H

#include <chrono>
#include <vector>
#include <string>

namespace medallion {

using Timestamp = std::chrono::nanoseconds;

/**
 * Latency measurement for a single order.
 */
struct LatencyMeasurement {
    uint64_t order_id;
    std::string phase;               // "submit", "confirmation", "fill"
    Timestamp latency_ns;            // Latency in nanoseconds
    Timestamp wall_time;             // Absolute time of measurement
};

/**
 * LatencyMonitor class.
 * Tracks and aggregates latency metrics.
 */
class LatencyMonitor {
public:
    LatencyMonitor();
    ~LatencyMonitor();

    /**
     * Record a latency measurement.
     * 
     * @param order_id Order ID
     * @param phase Execution phase ("submit", "confirmation", "fill")
     * @param latency_ns Latency in nanoseconds
     */
    void record_latency(uint64_t order_id, const std::string& phase, Timestamp latency_ns);

    /**
     * Get mean latency for a phase (in microseconds).
     */
    double get_mean_latency(const std::string& phase) const;

    /**
     * Get p99 latency for a phase (in microseconds).
     */
    double get_p99_latency(const std::string& phase) const;

    /**
     * Get p95 latency for a phase (in microseconds).
     */
    double get_p95_latency(const std::string& phase) const;

    /**
     * Get p50 (median) latency for a phase (in microseconds).
     */
    double get_p50_latency(const std::string& phase) const;

    /**
     * Get max latency for a phase (in microseconds).
     */
    double get_max_latency(const std::string& phase) const;

    /**
     * Get count of measurements for a phase.
     */
    size_t get_measurement_count(const std::string& phase) const;

    /**
     * Reset all measurements.
     */
    void reset();

    /**
     * Get human-readable summary.
     */
    std::string get_summary() const;

private:
    // Measurements by phase
    std::vector<LatencyMeasurement> measurements_;
    
    /**
     * Compute percentile latency.
     */
    double compute_percentile(const std::string& phase, int percentile) const;
};

}  // namespace medallion

#endif  // MEDALLION_LATENCY_MONITOR_H

#include "latency_monitor.h"
#include <algorithm>
#include <numeric>
#include <cmath>
#include <iomanip>
#include <sstream>

namespace medallion {

LatencyMonitor::LatencyMonitor()
    : measurements_() {}

LatencyMonitor::~LatencyMonitor() {}

void LatencyMonitor::record_latency(uint64_t order_id, const std::string& phase, Timestamp latency_ns) {
    auto wall_time = std::chrono::high_resolution_clock::now().time_since_epoch();
    measurements_.push_back({
        order_id,
        phase,
        latency_ns,
        std::chrono::duration_cast<Timestamp>(wall_time)
    });
}

double LatencyMonitor::get_mean_latency(const std::string& phase) const {
    std::vector<double> latencies;
    for (const auto& m : measurements_) {
        if (m.phase == phase) {
            latencies.push_back(m.latency_ns.count() / 1000.0);  // Convert ns to us
        }
    }

    if (latencies.empty()) return 0.0;

    double sum = std::accumulate(latencies.begin(), latencies.end(), 0.0);
    return sum / latencies.size();
}

double LatencyMonitor::get_p99_latency(const std::string& phase) const {
    return compute_percentile(phase, 99);
}

double LatencyMonitor::get_p95_latency(const std::string& phase) const {
    return compute_percentile(phase, 95);
}

double LatencyMonitor::get_p50_latency(const std::string& phase) const {
    return compute_percentile(phase, 50);
}

double LatencyMonitor::get_max_latency(const std::string& phase) const {
    std::vector<double> latencies;
    for (const auto& m : measurements_) {
        if (m.phase == phase) {
            latencies.push_back(m.latency_ns.count() / 1000.0);
        }
    }

    if (latencies.empty()) return 0.0;
    return *std::max_element(latencies.begin(), latencies.end());
}

size_t LatencyMonitor::get_measurement_count(const std::string& phase) const {
    size_t count = 0;
    for (const auto& m : measurements_) {
        if (m.phase == phase) count++;
    }
    return count;
}

void LatencyMonitor::reset() {
    measurements_.clear();
}

std::string LatencyMonitor::get_summary() const {
    std::ostringstream oss;
    oss << "Latency Monitor Summary\n"
        << "=======================\n";

    // Collect unique phases
    std::vector<std::string> phases;
    for (const auto& m : measurements_) {
        if (std::find(phases.begin(), phases.end(), m.phase) == phases.end()) {
            phases.push_back(m.phase);
        }
    }

    for (const auto& phase : phases) {
        oss << "\nPhase: " << phase << "\n"
            << "  Count:     " << get_measurement_count(phase) << "\n"
            << "  Mean:      " << std::fixed << std::setprecision(2)
            << get_mean_latency(phase) << " us\n"
            << "  P50:       " << get_p50_latency(phase) << " us\n"
            << "  P95:       " << get_p95_latency(phase) << " us\n"
            << "  P99:       " << get_p99_latency(phase) << " us\n"
            << "  Max:       " << get_max_latency(phase) << " us\n";
    }

    return oss.str();
}

double LatencyMonitor::compute_percentile(const std::string& phase, int percentile) const {
    std::vector<double> latencies;
    for (const auto& m : measurements_) {
        if (m.phase == phase) {
            latencies.push_back(m.latency_ns.count() / 1000.0);  // ns to us
        }
    }

    if (latencies.empty()) return 0.0;

    std::sort(latencies.begin(), latencies.end());

    size_t index = (latencies.size() * percentile) / 100;
    if (index >= latencies.size()) index = latencies.size() - 1;

    return latencies[index];
}

}  // namespace medallion

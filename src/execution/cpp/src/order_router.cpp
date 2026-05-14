#include "order_router.h"
#include <iostream>
#include <algorithm>
#include <iomanip>

namespace medallion {

OrderRouter::OrderRouter()
    : total_orders_submitted_(0),
      total_orders_filled_(0),
      total_volume_(0.0) {}

OrderRouter::~OrderRouter() {}

ExecutionReport OrderRouter::submit_order(const Order& order) {
    // Validate order
    if (order.quantity <= 0) {
        return ExecutionReport{
            order.id,
            "REJECTED",
            0.0,
            0.0,
            std::chrono::nanoseconds(0),
            "Invalid quantity",
            -1,
            0.0
        };
    }

    // Find best venue for this order
    int venue_id = select_best_venue(order);
    if (venue_id == -1) {
        return ExecutionReport{
            order.id,
            "REJECTED",
            0.0,
            0.0,
            std::chrono::nanoseconds(0),
            "No available venues",
            -1,
            0.0
        };
    }

    // Route to venue
    ExecutionReport report = route_to_venue(order, venue_id);
    
    // Track statistics
    total_orders_submitted_++;
    if (report.filled_quantity > 0) {
        total_orders_filled_++;
        total_volume_ += report.filled_quantity;
    }

    return report;
}

bool OrderRouter::cancel_order(OrderID order_id) {
    // Find and remove order from pending
    auto it = std::find_if(
        pending_orders_.begin(),
        pending_orders_.end(),
        [order_id](const Order& o) { return o.id == order_id; }
    );

    if (it != pending_orders_.end()) {
        pending_orders_.erase(it);
        return true;
    }
    return false;
}

ExecutionReport OrderRouter::get_order_status(OrderID order_id) {
    auto it = std::find_if(
        execution_history_.begin(),
        execution_history_.end(),
        [order_id](const ExecutionReport& r) { return r.order_id == order_id; }
    );

    if (it != execution_history_.end()) {
        return *it;
    }

    return ExecutionReport{
        order_id,
        "UNKNOWN",
        0.0,
        0.0,
        std::chrono::nanoseconds(0),
        "Order not found",
        -1,
        0.0
    };
}

void OrderRouter::register_venue(const Venue& venue) {
    venues_.push_back(venue);
}

std::vector<Venue> OrderRouter::get_available_venues() const {
    std::vector<Venue> available;
    for (const auto& v : venues_) {
        if (v.is_available) {
            available.push_back(v);
        }
    }
    return available;
}

std::string OrderRouter::get_stats_summary() const {
    std::ostringstream oss;
    oss << "OrderRouter Statistics\n"
        << "======================\n"
        << "Total Orders Submitted: " << total_orders_submitted_ << "\n"
        << "Total Orders Filled: " << total_orders_filled_ << "\n"
        << "Total Volume: " << std::fixed << std::setprecision(2) << total_volume_ << "\n"
        << "Fill Rate: " 
        << (total_orders_submitted_ > 0 ? 
            (100.0 * total_orders_filled_ / total_orders_submitted_) : 0.0)
        << "%\n"
        << "Active Venues: " << get_available_venues().size() << "\n";
    return oss.str();
}

int OrderRouter::select_best_venue(const Order& order) {
    auto available = get_available_venues();
    if (available.empty()) return -1;

    // Simple selection: lowest latency + lowest commission
    int best_venue = available[0].id;
    double best_score = available[0].latency_ms + available[0].commission_bps;

    for (const auto& v : available) {
        double score = v.latency_ms + v.commission_bps;
        if (score < best_score) {
            best_score = score;
            best_venue = v.id;
        }
    }

    return best_venue;
}

ExecutionReport OrderRouter::route_to_venue(const Order& order, int venue_id) {
    // Find the venue
    auto it = std::find_if(
        venues_.begin(),
        venues_.end(),
        [venue_id](const Venue& v) { return v.id == venue_id; }
    );

    if (it == venues_.end()) {
        return ExecutionReport{
            order.id,
            "REJECTED",
            0.0,
            0.0,
            std::chrono::nanoseconds(0),
            "Venue not found",
            -1,
            0.0
        };
    }

    // Simulated execution (stub)
    // In production: Send FIX/REST message to venue and wait for confirmation
    ExecutionReport report{
        order.id,
        "FILLED",                           // Assume filled for demo
        order.quantity,
        order.price > 0 ? order.price : 2000.0,  // Use order price or default
        std::chrono::nanoseconds(0),
        "",
        venue_id,
        (order.quantity * it->commission_bps) / 10000.0
    };

    // Store in history
    execution_history_.push_back(report);
    pending_orders_.push_back(order);

    return report;
}

}  // namespace medallion

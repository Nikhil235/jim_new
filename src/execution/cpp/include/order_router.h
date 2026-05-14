/*
 * Order Router Header
 * =====================
 * Ultra-low latency order routing to execution venues.
 * Responsible for:
 *  - Order validation
 *  - Venue selection (FX, CME, Crypto exchanges)
 *  - Route optimization (latency + fees)
 *  - Order submission and tracking
 */

#ifndef MEDALLION_ORDER_ROUTER_H
#define MEDALLION_ORDER_ROUTER_H

#include <vector>
#include <string>
#include <memory>
#include <cstdint>
#include <chrono>

namespace medallion {

// Forward declarations
struct Order;
struct ExecutionReport;
struct Venue;

using OrderID = uint64_t;
using Timestamp = std::chrono::nanoseconds;

/**
 * Order structure.
 * Represents a single order to be routed to an execution venue.
 */
struct Order {
    OrderID id;
    std::string symbol;           // "GC=F" (gold futures) or "XAUUSD" (spot)
    std::string side;              // "BUY" or "SELL"
    double quantity;               // Lots or contracts
    double price;                  // Limit price (0 for market)
    Timestamp created_at;          // Order creation timestamp
    std::string order_type;        // "MARKET", "LIMIT", "STOP"
    int venue_id;                  // Target venue (-1 = smart routing)
};

/**
 * Execution report from a venue.
 * Contains fill confirmations, partial fills, rejections, etc.
 */
struct ExecutionReport {
    OrderID order_id;
    std::string status;            // "ACCEPTED", "FILLED", "PARTIAL_FILL", "REJECTED", "CANCELLED"
    double filled_quantity;
    double fill_price;
    Timestamp execution_time;
    std::string rejection_reason;  // If REJECTED
    int venue_id;
    double commission;             // Execution cost
};

/**
 * Venue structure.
 * Represents an execution venue (exchange, broker).
 */
struct Venue {
    int id;
    std::string name;              // "CME", "FOREX_BROKER", "CRYPTO_EXCHANGE"
    std::string connection_type;   // "FIX", "REST", "WEBSOCKET"
    double latency_ms;             // Estimated round-trip latency
    double commission_bps;         // Commission in basis points
    bool is_available;
};

/**
 * OrderRouter class.
 * Central order routing engine.
 */
class OrderRouter {
public:
    OrderRouter();
    ~OrderRouter();

    /**
     * Submit an order for execution.
     * 
     * @param order The order to submit
     * @return Execution report with confirmation status
     */
    ExecutionReport submit_order(const Order& order);

    /**
     * Cancel a pending order.
     * 
     * @param order_id Order ID to cancel
     * @return true if cancellation accepted, false otherwise
     */
    bool cancel_order(OrderID order_id);

    /**
     * Get status of a submitted order.
     * 
     * @param order_id Order ID to query
     * @return Latest execution report for the order
     */
    ExecutionReport get_order_status(OrderID order_id);

    /**
     * Register a venue for routing.
     * 
     * @param venue The venue to register
     */
    void register_venue(const Venue& venue);

    /**
     * Get list of available venues.
     */
    std::vector<Venue> get_available_venues() const;

    /**
     * Get routing statistics.
     */
    std::string get_stats_summary() const;

private:
    // Venues
    std::vector<Venue> venues_;
    
    // Pending orders
    std::vector<Order> pending_orders_;
    
    // Order status tracking
    std::vector<ExecutionReport> execution_history_;
    
    // Statistics
    uint64_t total_orders_submitted_;
    uint64_t total_orders_filled_;
    double total_volume_;
    
    /**
     * Smart routing: select best venue for an order.
     */
    int select_best_venue(const Order& order);
    
    /**
     * Route order to venue (stub).
     */
    ExecutionReport route_to_venue(const Order& order, int venue_id);
};

}  // namespace medallion

#endif  // MEDALLION_ORDER_ROUTER_H

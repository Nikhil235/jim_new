/*
 * Demo: Order Router & Order Book
 * ================================
 * Simple demonstration of the C++ execution engine components.
 */

#include "order_router.h"
#include "order_book.h"
#include "latency_monitor.h"
#include <iostream>
#include <chrono>
#include <thread>

using namespace medallion;

int main() {
    std::cout << "========================================\n"
              << "Mini-Medallion C++ Execution Engine\n"
              << "Demo: Order Router & Order Book\n"
              << "========================================\n\n";

    // Initialize order router
    OrderRouter router;

    // Register venues
    router.register_venue({
        1,
        "CME GLOBEX",
        "FIX",
        0.5,  // latency ms
        1.0,  // commission bps
        true
    });

    router.register_venue({
        2,
        "FOREX BROKER",
        "REST",
        2.0,
        0.5,
        true
    });

    std::cout << "[OrderRouter] Registered " 
              << router.get_available_venues().size() 
              << " venues\n\n";

    // Initialize order book
    OrderBook book("XAUUSD");

    // Populate order book
    std::cout << "[OrderBook] Initializing order book...\n";
    book.add_order("BUY", 2000.00, 10.0);
    book.add_order("BUY", 1999.95, 20.0);
    book.add_order("BUY", 1999.90, 15.0);

    book.add_order("SELL", 2000.10, 12.0);
    book.add_order("SELL", 2000.15, 18.0);
    book.add_order("SELL", 2000.20, 25.0);

    std::cout << book.get_snapshot(3) << "\n";

    // Initialize latency monitor
    LatencyMonitor latency_monitor;

    // Simulate orders
    std::cout << "[OrderRouter] Submitting sample orders...\n";
    for (int i = 1; i <= 3; ++i) {
        Order order{
            static_cast<uint64_t>(i),
            "XAUUSD",
            (i % 2 == 0) ? "BUY" : "SELL",
            10.0,
            2000.0 + (i - 1) * 0.1,
            std::chrono::nanoseconds(0),
            "LIMIT"
        };

        // Measure latency
        auto start = std::chrono::high_resolution_clock::now();
        auto report = router.submit_order(order);
        auto end = std::chrono::high_resolution_clock::now();
        auto latency = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);

        latency_monitor.record_latency(order.id, "submit", latency);

        std::cout << "  Order " << order.id << ": " << report.status 
                  << " at " << report.fill_price 
                  << " (latency: " << latency.count() << " ns)\n";
    }

    std::cout << "\n" << router.get_stats_summary() << "\n";
    std::cout << "\n" << latency_monitor.get_summary() << "\n";

    std::cout << "========================================\n"
              << "Demo completed successfully!\n"
              << "========================================\n";

    return 0;
}

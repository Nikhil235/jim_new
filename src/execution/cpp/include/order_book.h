/*
 * Order Book Header
 * ==================
 * In-memory Level 3 (full) order book maintenance.
 * Used for:
 *  - Market microstructure analysis
 *  - Real-time tick-by-tick reconstruction
 *  - Spread/depth analysis
 */

#ifndef MEDALLION_ORDER_BOOK_H
#define MEDALLION_ORDER_BOOK_H

#include <vector>
#include <map>
#include <string>
#include <memory>
#include <cstdint>
#include <chrono>

namespace medallion {

using Timestamp = std::chrono::nanoseconds;

/**
 * Single order book level (bid or ask).
 */
struct PriceLevel {
    double price;
    double quantity;
    int order_count;  // Number of orders at this price
};

/**
 * OrderBook class.
 * Maintains bid/ask sides of an order book.
 */
class OrderBook {
public:
    OrderBook(const std::string& symbol);
    ~OrderBook();

    /**
     * Add an order to the book (buy or sell).
     * 
     * @param side "BUY" or "SELL"
     * @param price Limit price
     * @param quantity Order quantity
     */
    void add_order(const std::string& side, double price, double quantity);

    /**
     * Remove an order from the book.
     * 
     * @param side "BUY" or "SELL"
     * @param price Limit price
     * @param quantity Quantity to remove
     */
    void remove_order(const std::string& side, double price, double quantity);

    /**
     * Update an order (cancel and re-add at new price/qty).
     */
    void update_order(const std::string& side, double old_price, double new_price, double new_quantity);

    /**
     * Get best bid.
     */
    double get_best_bid() const;

    /**
     * Get best ask.
     */
    double get_best_ask() const;

    /**
     * Get bid-ask spread (in price units).
     */
    double get_spread() const;

    /**
     * Get mid-price.
     */
    double get_mid_price() const;

    /**
     * Get top N levels of the book.
     * 
     * @param side "BUY" or "SELL"
     * @param depth Number of levels to return
     */
    std::vector<PriceLevel> get_levels(const std::string& side, int depth) const;

    /**
     * Get total liquidity at a price level.
     */
    double get_liquidity_at(const std::string& side, double price) const;

    /**
     * Get total bid/ask volume.
     */
    double get_bid_volume() const;
    double get_ask_volume() const;

    /**
     * Clear the entire book.
     */
    void clear();

    /**
     * Get human-readable snapshot.
     */
    std::string get_snapshot(int depth = 5) const;

    /**
     * Get symbol.
     */
    std::string get_symbol() const { return symbol_; }

private:
    std::string symbol_;
    
    // Bid side: price -> quantity (map keeps sorted by price descending)
    std::map<double, double, std::greater<double>> bid_levels_;
    
    // Ask side: price -> quantity (map keeps sorted by price ascending)
    std::map<double, double> ask_levels_;
    
    // Stats
    uint64_t update_count_;
};

}  // namespace medallion

#endif  // MEDALLION_ORDER_BOOK_H

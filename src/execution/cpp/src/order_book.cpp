#include "order_book.h"
#include <sstream>
#include <iomanip>

namespace medallion {

OrderBook::OrderBook(const std::string& symbol)
    : symbol_(symbol), update_count_(0) {}

OrderBook::~OrderBook() {}

void OrderBook::add_order(const std::string& side, double price, double quantity) {
    if (side == "BUY") {
        if (bid_levels_.find(price) != bid_levels_.end()) {
            bid_levels_[price] += quantity;
        } else {
            bid_levels_[price] = quantity;
        }
    } else if (side == "SELL") {
        if (ask_levels_.find(price) != ask_levels_.end()) {
            ask_levels_[price] += quantity;
        } else {
            ask_levels_[price] = quantity;
        }
    }
    update_count_++;
}

void OrderBook::remove_order(const std::string& side, double price, double quantity) {
    if (side == "BUY") {
        auto it = bid_levels_.find(price);
        if (it != bid_levels_.end()) {
            it->second -= quantity;
            if (it->second <= 0) {
                bid_levels_.erase(it);
            }
        }
    } else if (side == "SELL") {
        auto it = ask_levels_.find(price);
        if (it != ask_levels_.end()) {
            it->second -= quantity;
            if (it->second <= 0) {
                ask_levels_.erase(it);
            }
        }
    }
    update_count_++;
}

void OrderBook::update_order(const std::string& side, double old_price, double new_price, double new_quantity) {
    remove_order(side, old_price, 1e9);  // Remove all at old price
    add_order(side, new_price, new_quantity);
}

double OrderBook::get_best_bid() const {
    if (bid_levels_.empty()) return 0.0;
    return bid_levels_.begin()->first;
}

double OrderBook::get_best_ask() const {
    if (ask_levels_.empty()) return 0.0;
    return ask_levels_.begin()->first;
}

double OrderBook::get_spread() const {
    double bid = get_best_bid();
    double ask = get_best_ask();
    if (bid == 0.0 || ask == 0.0) return 0.0;
    return ask - bid;
}

double OrderBook::get_mid_price() const {
    double bid = get_best_bid();
    double ask = get_best_ask();
    if (bid == 0.0 || ask == 0.0) return 0.0;
    return (bid + ask) / 2.0;
}

std::vector<PriceLevel> OrderBook::get_levels(const std::string& side, int depth) const {
    std::vector<PriceLevel> levels;

    if (side == "BUY") {
        int count = 0;
        for (const auto& [price, qty] : bid_levels_) {
            if (count >= depth) break;
            levels.push_back({price, qty, 1});
            count++;
        }
    } else if (side == "SELL") {
        int count = 0;
        for (const auto& [price, qty] : ask_levels_) {
            if (count >= depth) break;
            levels.push_back({price, qty, 1});
            count++;
        }
    }

    return levels;
}

double OrderBook::get_liquidity_at(const std::string& side, double price) const {
    if (side == "BUY") {
        auto it = bid_levels_.find(price);
        return it != bid_levels_.end() ? it->second : 0.0;
    } else if (side == "SELL") {
        auto it = ask_levels_.find(price);
        return it != ask_levels_.end() ? it->second : 0.0;
    }
    return 0.0;
}

double OrderBook::get_bid_volume() const {
    double total = 0.0;
    for (const auto& [price, qty] : bid_levels_) {
        total += qty;
    }
    return total;
}

double OrderBook::get_ask_volume() const {
    double total = 0.0;
    for (const auto& [price, qty] : ask_levels_) {
        total += qty;
    }
    return total;
}

void OrderBook::clear() {
    bid_levels_.clear();
    ask_levels_.clear();
    update_count_++;
}

std::string OrderBook::get_snapshot(int depth) const {
    std::ostringstream oss;
    oss << "OrderBook Snapshot: " << symbol_ << "\n"
        << "====================\n"
        << "Bid Side (Top " << depth << "):\n";

    auto bid_levels = get_levels("BUY", depth);
    for (const auto& level : bid_levels) {
        oss << std::fixed << std::setprecision(2)
            << "  " << level.price << " x " << level.quantity << "\n";
    }

    oss << "\nAsk Side (Top " << depth << "):\n";
    auto ask_levels = get_levels("SELL", depth);
    for (const auto& level : ask_levels) {
        oss << std::fixed << std::setprecision(2)
            << "  " << level.price << " x " << level.quantity << "\n";
    }

    oss << "\nSpread: " << std::fixed << std::setprecision(4) << get_spread() << "\n"
        << "Mid: " << get_mid_price() << "\n"
        << "Bid Volume: " << get_bid_volume() << "\n"
        << "Ask Volume: " << get_ask_volume() << "\n"
        << "Updates: " << update_count_ << "\n";

    return oss.str();
}

}  // namespace medallion

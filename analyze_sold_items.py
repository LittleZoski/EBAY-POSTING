"""
Market Analysis Tool for eBay Sold Items
Analyzes sold items data and provides actionable recommendations
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any


class MarketAnalyzer:
    """Analyzes eBay sold items data for market insights"""

    def __init__(self, data_file: str):
        """Load sold items data"""
        with open(data_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.orders = self.data.get("orders", [])
        self.summary = self.data.get("summary", {})

    def categorize_products(self) -> Dict[str, Dict]:
        """Categorize products by type/category"""
        categories = defaultdict(lambda: {
            "items": [],
            "total_sold": 0,
            "total_revenue": 0,
            "avg_price": 0,
            "sales_count": 0
        })

        for order in self.orders:
            for item in order.get("items", []):
                title = item.get("title", "").lower()
                price = item.get("soldPrice", 0)
                quantity = item.get("quantity", 1)

                # Categorize based on keywords in title
                category = self._categorize_by_title(title)

                categories[category]["items"].append({
                    "title": item.get("title", ""),
                    "price": price,
                    "quantity": quantity,
                    "sku": item.get("sku", ""),
                    "date": item.get("soldDate", "")
                })
                categories[category]["total_sold"] += quantity
                categories[category]["total_revenue"] += price
                categories[category]["sales_count"] += 1

        # Calculate averages
        for cat in categories.values():
            if cat["sales_count"] > 0:
                cat["avg_price"] = cat["total_revenue"] / cat["sales_count"]

        return dict(categories)

    def _categorize_by_title(self, title: str) -> str:
        """Categorize product by analyzing title keywords"""
        title_lower = title.lower()

        # Beauty & Skincare
        if any(word in title_lower for word in [
            "serum", "cream", "collagen", "wrinkle", "anti-aging", "moisturizer",
            "skin", "facial", "firming", "hydrating", "acid", "vitamin"
        ]):
            return "Beauty & Skincare"

        # Hair Care
        if any(word in title_lower for word in [
            "shampoo", "conditioner", "hair", "scalp", "detangler", "protein",
            "rice water", "volumizing", "strengthening"
        ]):
            return "Hair Care"

        # Body Care
        if any(word in title_lower for word in [
            "body spray", "body serum", "exfoliating", "towel", "scrubber",
            "bump", "salicylic", "body care"
        ]):
            return "Body Care"

        # Lip Care & Makeup
        if any(word in title_lower for word in [
            "lip", "gloss", "balm", "lipstick", "makeup", "cosmetic"
        ]):
            return "Lip Care & Makeup"

        # Pet Care
        if any(word in title_lower for word in [
            "dog", "cat", "pet", "puppy", "veterinary", "mushroom powder",
            "horse", "fly spray", "liniment"
        ]):
            return "Pet Care"

        # Kitchen & Home
        if any(word in title_lower for word in [
            "kitchen", "mixer", "funnel", "home", "appliance"
        ]):
            return "Kitchen & Home"

        # Health & Wellness
        if any(word in title_lower for word in [
            "slim", "patches", "weight", "health", "wellness", "supplement"
        ]):
            return "Health & Wellness"

        # Toner & Pads
        if any(word in title_lower for word in [
            "toner", "pad", "exfoliate", "pha"
        ]):
            return "Toner & Pads"

        # Collectibles & Hobbies
        if any(word in title_lower for word in [
            "warhammer", "40k", "tau", "miniature", "collectible"
        ]):
            return "Collectibles & Hobbies"

        return "Other"

    def analyze_top_performers(self, categories: Dict) -> List[Dict]:
        """Identify top performing categories"""
        performance = []

        for category, data in categories.items():
            performance.append({
                "category": category,
                "total_revenue": data["total_revenue"],
                "units_sold": data["total_sold"],
                "avg_price": data["avg_price"],
                "sales_count": data["sales_count"],
                "revenue_per_sale": data["total_revenue"] / data["sales_count"] if data["sales_count"] > 0 else 0
            })

        # Sort by total revenue
        performance.sort(key=lambda x: x["total_revenue"], reverse=True)
        return performance

    def find_best_selling_skus(self) -> List[Dict]:
        """Find best-selling individual SKUs"""
        sku_performance = defaultdict(lambda: {
            "sku": "",
            "title": "",
            "units_sold": 0,
            "total_revenue": 0,
            "sales_count": 0,
            "avg_price": 0
        })

        for order in self.orders:
            for item in order.get("items", []):
                sku = item.get("sku", "")
                if not sku:  # Skip items without SKU
                    continue

                title = item.get("title", "")
                price = item.get("soldPrice", 0)
                quantity = item.get("quantity", 1)

                sku_performance[sku]["sku"] = sku
                sku_performance[sku]["title"] = title
                sku_performance[sku]["units_sold"] += quantity
                sku_performance[sku]["total_revenue"] += price
                sku_performance[sku]["sales_count"] += 1

        # Calculate averages
        for data in sku_performance.values():
            if data["sales_count"] > 0:
                data["avg_price"] = data["total_revenue"] / data["sales_count"]

        # Convert to list and sort
        performance_list = list(sku_performance.values())
        performance_list.sort(key=lambda x: x["units_sold"], reverse=True)

        return performance_list

    def analyze_price_points(self) -> Dict:
        """Analyze which price points sell best"""
        price_ranges = {
            "$0-20": {"count": 0, "revenue": 0},
            "$20-40": {"count": 0, "revenue": 0},
            "$40-60": {"count": 0, "revenue": 0},
            "$60-100": {"count": 0, "revenue": 0},
            "$100+": {"count": 0, "revenue": 0}
        }

        for order in self.orders:
            for item in order.get("items", []):
                price = item.get("soldPrice", 0)

                if price < 20:
                    range_key = "$0-20"
                elif price < 40:
                    range_key = "$20-40"
                elif price < 60:
                    range_key = "$40-60"
                elif price < 100:
                    range_key = "$60-100"
                else:
                    range_key = "$100+"

                price_ranges[range_key]["count"] += item.get("quantity", 1)
                price_ranges[range_key]["revenue"] += price

        return price_ranges

    def generate_recommendations(self, categories: Dict, top_performers: List, top_skus: List) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Top performing category
        if top_performers:
            top_cat = top_performers[0]
            recommendations.append(
                f"FOCUS ON: {top_cat['category']} is your #1 revenue generator "
                f"(${top_cat['total_revenue']:.2f} from {top_cat['units_sold']} units). "
                f"List MORE products in this category!"
            )

        # Underperforming but present categories
        if len(top_performers) > 1:
            low_performers = [p for p in top_performers if p['sales_count'] < 3 and p['sales_count'] > 0]
            if low_performers:
                recommendations.append(
                    f"REDUCE: Categories with <3 sales may not be worth your time: "
                    f"{', '.join([p['category'] for p in low_performers[:3]])}"
                )

        # Best selling SKU
        if top_skus and top_skus[0]['units_sold'] > 2:
            best_sku = top_skus[0]
            recommendations.append(
                f"WINNING PRODUCT: '{best_sku['title'][:60]}...' sold {best_sku['units_sold']} units "
                f"(${best_sku['total_revenue']:.2f} revenue). Find similar products!"
            )

        # Multiple sales indicators
        repeat_sellers = [s for s in top_skus if s['sales_count'] >= 3]
        if repeat_sellers:
            recommendations.append(
                f"PROVEN SELLERS: {len(repeat_sellers)} SKUs sold 3+ times. "
                f"These are your reliable income - keep them in stock!"
            )

        # Price point analysis
        beauty_skincare = categories.get("Beauty & Skincare", {})
        if beauty_skincare.get("sales_count", 0) > 0:
            avg_beauty_price = beauty_skincare.get("avg_price", 0)
            recommendations.append(
                f"BEAUTY PRICING: Your average beauty/skincare sale is ${avg_beauty_price:.2f}. "
                f"Target products in the $30-50 range for optimal conversion."
            )

        return recommendations

    def print_analysis(self):
        """Print comprehensive analysis report"""
        print("\n" + "="*80)
        print("EBAY MARKET ANALYSIS REPORT")
        print("="*80)

        # Overall summary
        print(f"\nOVERALL PERFORMANCE:")
        print(f"  Total Orders: {self.summary.get('totalOrders', 0)}")
        print(f"  Total Items Sold: {self.summary.get('totalItemsSold', 0)}")
        print(f"  Total Revenue: ${self.summary.get('totalRevenue', 0):,.2f}")
        print(f"  Average Order Value: ${self.summary.get('averageOrderValue', 0):.2f}")

        # Category analysis
        categories = self.categorize_products()
        top_performers = self.analyze_top_performers(categories)

        print("\n" + "-"*80)
        print("CATEGORY PERFORMANCE (by Revenue)")
        print("-"*80)
        print(f"{'Category':<25} {'Revenue':<15} {'Units':<10} {'Sales':<10} {'Avg Price':<12}")
        print("-"*80)

        for perf in top_performers:
            print(f"{perf['category']:<25} "
                  f"${perf['total_revenue']:<14,.2f} "
                  f"{perf['units_sold']:<10} "
                  f"{perf['sales_count']:<10} "
                  f"${perf['avg_price']:<11,.2f}")

        # Top SKUs
        top_skus = self.find_best_selling_skus()

        print("\n" + "-"*80)
        print("TOP 10 BEST-SELLING PRODUCTS")
        print("-"*80)
        print(f"{'Product':<50} {'Units':<10} {'Revenue':<12}")
        print("-"*80)

        for sku in top_skus[:10]:
            title_short = sku['title'][:47] + "..." if len(sku['title']) > 50 else sku['title']
            print(f"{title_short:<50} {sku['units_sold']:<10} ${sku['total_revenue']:<11,.2f}")

        # Price point analysis
        price_ranges = self.analyze_price_points()

        print("\n" + "-"*80)
        print("PRICE POINT ANALYSIS")
        print("-"*80)
        print(f"{'Price Range':<15} {'Units Sold':<15} {'Revenue':<15}")
        print("-"*80)

        for range_name, data in price_ranges.items():
            if data['count'] > 0:
                print(f"{range_name:<15} {data['count']:<15} ${data['revenue']:<14,.2f}")

        # Recommendations
        recommendations = self.generate_recommendations(categories, top_performers, top_skus)

        print("\n" + "="*80)
        print("KEY RECOMMENDATIONS")
        print("="*80)

        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec}")

        print("\n" + "="*80)
        print("ACTIONABLE NEXT STEPS")
        print("="*80)
        print("\n1. Double down on Beauty & Skincare if it's your top category")
        print("2. Source more products similar to your best-sellers")
        print("3. Phase out categories with <3 sales in the analyzed period")
        print("4. Focus on products in the $20-60 price range (sweet spot)")
        print("5. Look for trending items in your winning categories on Amazon")
        print("6. Analyze seasonal trends - certain products may perform better at specific times")
        print("\n" + "="*80 + "\n")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        # Find most recent analysis file
        analysis_folder = Path("ebay_sold_items_analysis")
        if not analysis_folder.exists():
            print("Error: No analysis folder found. Run fetch_sold_items.py first.")
            sys.exit(1)

        json_files = sorted(analysis_folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not json_files:
            print("Error: No analysis files found. Run fetch_sold_items.py first.")
            sys.exit(1)

        data_file = json_files[0]
        print(f"Using most recent analysis file: {data_file.name}\n")

    try:
        analyzer = MarketAnalyzer(str(data_file))
        analyzer.print_analysis()
    except Exception as e:
        print(f"Error analyzing data: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

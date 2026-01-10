"""
Analyze token usage for OLD vs NEW category selection system
"""

import sys
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')

print("\n" + "="*70)
print("TOKEN COST ANALYSIS: OLD vs NEW Category Selection")
print("="*70)

# Load priority categories to count
with open('priority_categories.json', 'r', encoding='utf-8') as f:
    priority_data = json.load(f)

beauty_cats = priority_data['beauty_health']['categories']

print(f"\n📊 CATEGORY COUNTS:")
print(f"   OLD system: 250 categories sent to LLM")
print(f"   NEW system: ~300 categories sent to LLM")
print(f"      - Priority (beauty_health): {len(beauty_cats)} categories")
print(f"      - Sampled (diverse): ~260 categories")
print(f"      - Total: ~{len(beauty_cats) + 260} categories")

# Estimate token count per category
# Each category object has: id, name, path, level
# Example: {"id": "29618", "name": "Acne & Blemish Treatments", "path": "Root > Health & Beauty > Skin Care > Acne & Blemish Treatments", "level": 3}
# Approximate: 40-60 tokens per category

tokens_per_category_old = 50  # Average
tokens_per_category_new = 50

old_category_tokens = 250 * tokens_per_category_old
new_category_tokens = 300 * tokens_per_category_new

print(f"\n💰 TOKEN USAGE ESTIMATE:")
print(f"   OLD category list: ~{old_category_tokens:,} tokens")
print(f"   NEW category list: ~{new_category_tokens:,} tokens")
print(f"   Difference: +{new_category_tokens - old_category_tokens:,} tokens per product")

# Full prompt structure
print(f"\n📝 FULL PROMPT BREAKDOWN:")
print(f"   System instructions: ~300 tokens")
print(f"   Product data (title, desc, bullets): ~400 tokens")
print(f"   Category list:")
print(f"      OLD: ~{old_category_tokens:,} tokens")
print(f"      NEW: ~{new_category_tokens:,} tokens")
print(f"   Total prompt size:")
print(f"      OLD: ~{300 + 400 + old_category_tokens:,} tokens")
print(f"      NEW: ~{300 + 400 + new_category_tokens:,} tokens")

# LLM response is consistent (doesn't change)
llm_response_tokens = 100  # JSON output with title, brand, category_id

old_total = 300 + 400 + old_category_tokens + llm_response_tokens
new_total = 300 + 400 + new_category_tokens + llm_response_tokens

print(f"\n📊 TOTAL TOKENS PER PRODUCT:")
print(f"   OLD: ~{old_total:,} tokens")
print(f"   NEW: ~{new_total:,} tokens")
print(f"   Increase: +{new_total - old_total:,} tokens (+{((new_total - old_total) / old_total * 100):.1f}%)")

# Cost calculation (Claude Haiku pricing)
# Input: $0.25 per 1M tokens
# Output: $1.25 per 1M tokens

haiku_input_cost_per_1m = 0.25
haiku_output_cost_per_1m = 1.25

old_input_cost = ((old_total - llm_response_tokens) / 1_000_000) * haiku_input_cost_per_1m
old_output_cost = (llm_response_tokens / 1_000_000) * haiku_output_cost_per_1m
old_cost_per_product = old_input_cost + old_output_cost

new_input_cost = ((new_total - llm_response_tokens) / 1_000_000) * haiku_input_cost_per_1m
new_output_cost = (llm_response_tokens / 1_000_000) * haiku_output_cost_per_1m
new_cost_per_product = new_input_cost + new_output_cost

print(f"\n💵 COST PER PRODUCT (Claude Haiku):")
print(f"   OLD: ${old_cost_per_product:.6f}")
print(f"   NEW: ${new_cost_per_product:.6f}")
print(f"   Increase: +${new_cost_per_product - old_cost_per_product:.6f} per product")

# Cost for a batch of products
batch_sizes = [10, 42, 100]
print(f"\n📦 COST FOR BATCHES:")
for batch_size in batch_sizes:
    old_batch_cost = old_cost_per_product * batch_size
    new_batch_cost = new_cost_per_product * batch_size
    increase = new_batch_cost - old_batch_cost
    print(f"   {batch_size} products:")
    print(f"      OLD: ${old_batch_cost:.4f}")
    print(f"      NEW: ${new_batch_cost:.4f}")
    print(f"      Increase: +${increase:.4f}")

# Accuracy improvement value
print(f"\n🎯 VALUE ANALYSIS:")
print(f"   OLD accuracy: 73.8% (31/42 products)")
print(f"   Target accuracy: 95%+ (40/42 products)")
print(f"   Failed listings cost: $18 in listing fees (your recent mistake)")
print(f"")
print(f"   For 42 products:")
print(f"      OLD failures: 11 products @ ~$1.50/listing = ~$16.50 wasted")
print(f"      NEW failures (5% rate): 2 products @ ~$1.50/listing = ~$3.00 wasted")
print(f"      Savings from fewer failures: ~$13.50")
print(f"")
print(f"      NEW cost increase: +${(new_cost_per_product - old_cost_per_product) * 42:.4f}")
print(f"      Net benefit: ~${13.50 - ((new_cost_per_product - old_cost_per_product) * 42):.2f}")

print(f"\n" + "="*70)
print("✅ CONCLUSION:")
print("="*70)
print(f"Token cost increase is MINIMAL (~{((new_total - old_total) / old_total * 100):.1f}%) but accuracy")
print(f"improvement should be MASSIVE (73.8% → 95%+)")
print(f"")
print(f"The small increase in LLM costs (~${(new_cost_per_product - old_cost_per_product) * 42:.4f} for 42 products)")
print(f"is MORE than offset by avoiding failed listings (~$13.50 saved).")
print(f"\n" + "="*70 + "\n")

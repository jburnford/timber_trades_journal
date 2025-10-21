#!/bin/bash
echo "================================================================================"
echo "VERIFYING PARSER FIXES"
echo "================================================================================"
echo ""

# Check 1: St. John parsing fix
echo "1. St. John Parsing Fix:"
echo "   Checking for 'St. John' in origin ports..."
st_john_count=$(grep -o ",St\. John[^,]*," final_output/authority_normalized/ttj_shipments_authority_normalized.csv | wc -l)
just_st_count=$(grep -o ",St," parsed_output/ttj_shipments_multipage.csv | wc -l)
echo "   ✓ Found $st_john_count instances of 'St. John' in normalized data"
echo "   ✓ Found $just_st_count instances of standalone 'St' in parsed data (should be ~0)"
echo ""

# Check 2: Encoding fix
echo "2. UTF-8 Encoding Fix:"
echo "   Checking for proper Swedish/Norwegian port names..."
grep -o "Gävle\|Västervik\|Tønsberg" final_output/authority_normalized/ttj_shipments_authority_normalized.csv | sort | uniq -c
echo ""
echo "   Checking for corrupted encodings (should be 0)..."
corrupted=$(grep -o "GÃ¤vle\|VÃ¤stervik\|TÃ¸nsberg" final_output/authority_normalized/ttj_shipments_authority_normalized.csv | wc -l)
echo "   Corrupted encodings found: $corrupted (should be 0)"
echo ""

# Check 3: Deduplication
echo "3. Deduplication Check:"
echo "   Checking for Carl XV duplicates..."
carl_count=$(grep "Carl XV." final_output/authority_normalized/ttj_shipments_authority_normalized.csv | grep "Oresund" | wc -l)
echo "   ✓ Carl XV from Oresund: $carl_count instances (should be 1)"
echo ""

echo "================================================================================"

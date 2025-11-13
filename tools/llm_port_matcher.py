#!/usr/bin/env python3
"""
Use LLM to intelligently match database ports with GeoJSON ports.

Handles:
- Spelling variations
- Encoding issues
- Alternative historical names
- Rejecting incorrect fuzzy matches
- Identifying parsing errors vs real ports
"""

import json
import anthropic
import os
from pathlib import Path

def create_matching_prompt(fuzzy_matches, missing_ports, geojson_ports, port_type="destination"):
    """Create prompt for LLM to review port matches."""

    # Get list of all GeoJSON port names for reference
    geo_port_list = "\n".join(f"  - {port}" for port in sorted(geojson_ports.keys())[:100])

    prompt = f"""You are a historical geography expert specializing in 19th century maritime ports.

I'm matching port names from a historical shipping database (1874-1899 Timber Trades Journal) with a GeoJSON file containing port coordinates.

**Task 1: Review Fuzzy Matches**

These are ports where string similarity suggested a match, but I need you to confirm if they're actually the same port or different ports:

"""

    # Add fuzzy matches for review (top 30)
    for i, match in enumerate(fuzzy_matches[:30], 1):
        prompt += f"\n{i}. Database: '{match['db_port']}' <-> GeoJSON: '{match['geo_port']}'"
        prompt += f"\n   (Similarity: {match['similarity']:.2f}, Ships: {match['count']:,})"

    prompt += f"""

**Task 2: Match Missing Ports**

These ports appear in the database but weren't matched. For major ports (high ship counts), try to match them with GeoJSON ports:

"""

    # Add top missing ports (top 30)
    for i, port in enumerate(missing_ports[:30], 1):
        prompt += f"\n{i}. '{port['db_port']}' ({port['count']:,} ships)"

    prompt += f"""

**Available GeoJSON ports (first 100):**
{geo_port_list}
... (and {len(geojson_ports) - 100} more)

**Instructions:**

Return a JSON object with:

1. **confirmed_matches**: Array of fuzzy matches that are CORRECT (same port, just different spelling/encoding)
   Format: [{{"db_port": "...", "geo_port": "...", "reason": "..."}}]

2. **rejected_matches**: Array of fuzzy matches that are WRONG (different ports matched by mistake)
   Format: [{{"db_port": "...", "geo_port": "...", "reason": "..."}}]

3. **new_matches**: Array of missing ports you can match to GeoJSON ports
   Format: [{{"db_port": "...", "geo_port": "...", "reason": "..."}}]

4. **parsing_errors**: Array of database "ports" that are clearly parsing errors (not real ports)
   Format: [{{"db_port": "...", "reason": "..."}}]

5. **real_missing_ports**: Array of real ports that genuinely need geocoding added to GeoJSON
   Format: [{{"db_port": "...", "ship_count": ..., "suggested_coords": {{"lat": ..., "lon": ...}}, "reason": "..."}}]

**Guidelines:**
- For spelling variations (Kronstadt/Cronstadt, Sundsvall/Sundswall): CONFIRM match
- For encoding issues (Gävle/GÃ¤vle): CONFIRM match
- For alternative names (Arkhangelsk/Archangel): CONFIRM match
- For completely different ports (Deptford/Bideford, Lerwick/Limerick): REJECT match
- For parsing errors (LIMITED, JOINERY, SDD): Mark as parsing_errors
- For major real ports (Tyne, Quebec): Mark as real_missing_ports with suggested coordinates

Return ONLY the JSON object, no other text.
"""

    return prompt

def call_llm_matcher(prompt, api_key):
    """Call Claude API to match ports."""
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        temperature=0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # Parse JSON response
    # Remove markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    return json.loads(response_text)

def process_llm_results(llm_results, matches):
    """Process LLM results and update match data."""

    # Apply confirmed fuzzy matches
    for confirmed in llm_results.get('confirmed_matches', []):
        # Find the original fuzzy match
        for fuzzy in matches['fuzzy_destinations'] + matches['fuzzy_origins']:
            if fuzzy['db_port'] == confirmed['db_port']:
                # Move to perfect matches
                perfect_match = {
                    'db_port': fuzzy['db_port'],
                    'geo_port': confirmed['geo_port'],
                    'count': fuzzy['count'],
                    'coords': fuzzy['coords'],
                    'llm_confirmed': True,
                    'reason': confirmed.get('reason', '')
                }

                # Determine if destination or origin
                if fuzzy in matches['fuzzy_destinations']:
                    matches['perfect_destinations'].append(perfect_match)
                    matches['fuzzy_destinations'].remove(fuzzy)
                else:
                    matches['perfect_origins'].append(perfect_match)
                    matches['fuzzy_origins'].remove(fuzzy)
                break

    # Apply new matches
    for new_match in llm_results.get('new_matches', []):
        # Find in missing lists
        for missing in matches['missing_destinations'] + matches['missing_origins']:
            if missing['db_port'] == new_match['db_port']:
                # Need to look up coords from geojson_ports
                # This will be handled in the main function
                if missing in matches['missing_destinations']:
                    matches['missing_destinations'].remove(missing)
                else:
                    matches['missing_origins'].remove(missing)

                # Add to new_matches for later processing
                if 'llm_new_matches' not in matches:
                    matches['llm_new_matches'] = []
                matches['llm_new_matches'].append(new_match)
                break

    # Store parsing errors and real missing ports
    matches['parsing_errors'] = llm_results.get('parsing_errors', [])
    matches['real_missing_ports'] = llm_results.get('real_missing_ports', [])

    return matches

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    # Load previous matching results
    matches_path = base_dir / "analysis" / "port_geocoding_matches.json"
    with open(matches_path, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    # Load GeoJSON for port list
    with open(base_dir / "Ports_Master.geojson", 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    geojson_ports = {}
    for feature in geojson_data['features']:
        if feature['properties']['Name'] != 'Delete':
            port_name = feature['properties']['Name']
            coords = feature['geometry']['coordinates']
            geojson_ports[port_name] = {
                'longitude': coords[0],
                'latitude': coords[1]
            }

    print("=" * 80)
    print("LLM-ASSISTED PORT MATCHING")
    print("=" * 80)

    # Get API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("\nError: ANTHROPIC_API_KEY not set in environment")
        print("Please set: export ANTHROPIC_API_KEY='your-key-here'")
        return

    print(f"\nLoaded {len(matches['fuzzy_destinations'])} fuzzy destination matches")
    print(f"Loaded {len(matches['missing_destinations'])} missing destinations")
    print(f"Loaded {len(geojson_ports)} GeoJSON ports")

    # Process destinations
    print("\n" + "=" * 80)
    print("PROCESSING DESTINATIONS")
    print("=" * 80)

    prompt = create_matching_prompt(
        matches['fuzzy_destinations'],
        matches['missing_destinations'],
        geojson_ports,
        port_type="destination"
    )

    print("\nCalling LLM for destination analysis...")
    dest_results = call_llm_matcher(prompt, api_key)

    print(f"\nResults:")
    print(f"  Confirmed matches: {len(dest_results.get('confirmed_matches', []))}")
    print(f"  Rejected matches: {len(dest_results.get('rejected_matches', []))}")
    print(f"  New matches: {len(dest_results.get('new_matches', []))}")
    print(f"  Parsing errors: {len(dest_results.get('parsing_errors', []))}")
    print(f"  Real missing ports: {len(dest_results.get('real_missing_ports', []))}")

    # Process origins (limited to avoid token costs)
    print("\n" + "=" * 80)
    print("PROCESSING ORIGINS (TOP 50 FUZZY + TOP 50 MISSING)")
    print("=" * 80)

    prompt = create_matching_prompt(
        matches['fuzzy_origins'][:50],  # Limit to top 50
        matches['missing_origins'][:50],  # Limit to top 50
        geojson_ports,
        port_type="origin"
    )

    print("\nCalling LLM for origin analysis...")
    origin_results = call_llm_matcher(prompt, api_key)

    print(f"\nResults:")
    print(f"  Confirmed matches: {len(origin_results.get('confirmed_matches', []))}")
    print(f"  Rejected matches: {len(origin_results.get('rejected_matches', []))}")
    print(f"  New matches: {len(origin_results.get('new_matches', []))}")
    print(f"  Parsing errors: {len(origin_results.get('parsing_errors', []))}")
    print(f"  Real missing ports: {len(origin_results.get('real_missing_ports', []))}")

    # Save LLM results
    output_path = base_dir / "analysis" / "llm_port_matching_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'destinations': dest_results,
            'origins': origin_results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ LLM results saved to: {output_path}")

    # Show some examples
    print("\n" + "=" * 80)
    print("EXAMPLE CONFIRMED MATCHES")
    print("=" * 80)
    for match in dest_results.get('confirmed_matches', [])[:10]:
        print(f"\n{match['db_port']} → {match['geo_port']}")
        print(f"  Reason: {match.get('reason', 'N/A')}")

    print("\n" + "=" * 80)
    print("EXAMPLE PARSING ERRORS IDENTIFIED")
    print("=" * 80)
    for error in dest_results.get('parsing_errors', [])[:10]:
        print(f"\n{error['db_port']}")
        print(f"  Reason: {error.get('reason', 'N/A')}")

    print("\n" + "=" * 80)
    print("REAL MISSING PORTS NEEDING GEOCODING")
    print("=" * 80)
    for port in dest_results.get('real_missing_ports', [])[:10]:
        print(f"\n{port['db_port']} ({port.get('ship_count', 'N/A')} ships)")
        if 'suggested_coords' in port:
            print(f"  Suggested coords: {port['suggested_coords']}")
        print(f"  Reason: {port.get('reason', 'N/A')}")

if __name__ == '__main__':
    main()

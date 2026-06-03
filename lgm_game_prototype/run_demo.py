from lgm_game import LGMGameConfig, LGMGamePrototype


def main() -> None:
    config = LGMGameConfig(
        grid_size=4,
        top_k=3,
        geometry_weight=0.35,
        semantic_weight=0.30,
        map_weight=0.25,
        style_penalty_weight=0.20,
        clique_threshold=0.25,
    )
    model = LGMGamePrototype(config)

    label_grid = [
        "building",
        "building",
        "road",
        "vegetation",
        "building",
        "parking",
        "road intersection",
        "vegetation",
        "field",
        "field",
        "road",
        "water",
        "field",
        "building",
        "road",
        "water",
    ]

    uav_tokens = model.encode_visual_tokens("uav", "demo_campus", label_grid)
    satellite_tokens = model.encode_visual_tokens("sat", "demo_campus", label_grid)

    description = (
        "The scene contains several buildings, a road intersection, "
        "a sports field, vegetation blocks, parking area, and water boundary. "
        "The UAV image has strong shadow and summer vegetation style."
    )
    anchors = model.build_semantic_anchors(description)
    style_prompts = model.build_style_prompts(description)
    map_tokens = model.build_map_tokens(
        [
            {"id": "m_road_1", "category": "road", "x": 0.66, "y": 0.33, "confidence": 0.95},
            {"id": "m_field_1", "category": "field", "x": 0.25, "y": 0.75, "confidence": 0.90},
            {"id": "m_water_1", "category": "water", "x": 1.00, "y": 0.82, "confidence": 0.85},
            {"id": "m_building_1", "category": "building", "x": 0.18, "y": 0.18, "confidence": 0.88},
        ]
    )

    edges = model.topk_sparse_attention(
        uav_tokens, satellite_tokens, anchors, style_prompts, map_tokens
    )
    matches = model.sinkhorn_match(uav_tokens, satellite_tokens, edges)
    final_matches = model.greedy_consistency_clique(matches)

    print("=== Semantic Anchors ===")
    for anchor in anchors:
        print(f"{anchor.name:20s} weight={anchor.weight:.2f}")

    print("\n=== Style Prompts ===")
    for prompt in style_prompts:
        print(f"{prompt.name:20s} weight={prompt.weight:.2f}")

    print("\n=== Top Sparse Attention Edges (first 12) ===")
    for edge in edges[:12]:
        print(f"{edge.query_id:8s} -> {edge.ref_id:8s} score={edge.score:.3f}")

    print("\n=== Sinkhorn Matches ===")
    for match in matches:
        print(f"{match.query_id:8s} -> {match.ref_id:8s} confidence={match.confidence:.3f}")

    print("\n=== Consistent Final Matches ===")
    for match in final_matches:
        print(f"{match.query_id:8s} -> {match.ref_id:8s} confidence={match.confidence:.3f}")


if __name__ == "__main__":
    main()

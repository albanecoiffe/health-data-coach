def snapshot_matches(req_snapshot, start, end) -> bool:
    return (
        req_snapshot.period.start == start.isoformat()
        and req_snapshot.period.end == end.isoformat()
    )

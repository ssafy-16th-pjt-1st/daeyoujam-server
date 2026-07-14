def build_sources(places):
    return [{"place_id": place.id, "content_id": place.content_id, "title": place.title} for place in places]


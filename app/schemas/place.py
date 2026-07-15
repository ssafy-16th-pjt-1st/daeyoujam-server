from pydantic import BaseModel, ConfigDict


class PlaceRead(BaseModel):
    id: int
    content_id: int
    content_type_id: int | None = None
    content_type: str | None = None
    title: str
    addr1: str | None = None
    addr2: str | None = None
    zipcode: str | None = None
    tel: str | None = None
    mapx: float | None = None
    mapy: float | None = None
    mlevel: int | None = None
    first_image: str | None = None
    first_image2: str | None = None
    created_time: str | None = None
    modified_time: str | None = None
    copyright_type: str | None = None
    area_code: str | None = None
    sigungu_code: str | None = None
    region_code: str | None = None
    signgu_code: str | None = None
    category1: str | None = None
    category2: str | None = None
    category3: str | None = None
    lcls_system1: str | None = None
    lcls_system2: str | None = None
    lcls_system3: str | None = None
    average_rating: float = 0
    review_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PlaceListResponse(BaseModel):
    items: list[PlaceRead]
    total: int
    page: int
    size: int


class PlaceContentRead(BaseModel):
    content_id: int
    content_type_id: int | None = None
    title: str
    addr1: str | None = None
    tel: str | None = None
    mapx: float | None = None
    mapy: float | None = None
    first_image: str | None = None

    model_config = ConfigDict(from_attributes=True)

from types import SimpleNamespace

from app.ai.services.openai_service import _build_rag_chain, _format_documents, _ranked_places_to_documents
from app.ai.services.rag_service import RankedPlace


def test_ranked_places_are_converted_to_langchain_documents():
    place = SimpleNamespace(
        id=990,
        content_id=1796079,
        title="성심당",
        content_type="음식점",
        addr1="대전광역시 중구 대종로480번길 15",
        addr2="",
        first_image="https://example.com/image.jpg",
        first_image2=None,
        average_rating=4.3,
        review_count=36,
    )

    documents = _ranked_places_to_documents([RankedPlace(place=place, recommendation_reason="질문에서 직접 언급", score=10)])

    assert len(documents) == 1
    assert documents[0].metadata["place_id"] == 990
    assert documents[0].metadata["source"] == "places"
    assert "성심당" in documents[0].page_content
    assert "대전광역시 중구 대종로480번길 15" in documents[0].page_content


def test_format_documents_includes_rank_and_place_id():
    place = SimpleNamespace(
        id=1,
        content_id=2,
        title="테스트 장소",
        content_type="관광지",
        addr1="대전",
        addr2="",
        first_image=None,
        first_image2=None,
        average_rating=0,
        review_count=0,
    )
    documents = _ranked_places_to_documents([RankedPlace(place=place, recommendation_reason="테스트", score=1)])

    formatted = _format_documents(documents)

    assert "[1] place_id=1" in formatted
    assert "장소명: 테스트 장소" in formatted


def test_rag_chain_can_be_built_with_fake_llm():
    from langchain_core.runnables import RunnableLambda

    chain = _build_rag_chain(RunnableLambda(lambda _: "성심당은 대전광역시 중구 대종로480번길 15에 있어요."))

    assert chain is not None

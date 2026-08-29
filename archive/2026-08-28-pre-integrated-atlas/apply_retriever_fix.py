import io, os

PATH = os.path.join("src", "atlas", "pipeline", "session_runner.py")

OLD = '''def make_retriever(phase2_retriever) -> RetrieverFn:
    """
    Wrap a Phase 2 Retriever instance into the (artwork_id, query) -> list[dict]
    callable that SessionRunner expects.

    Usage in dependency_container.py:
        from atlas.pipeline.session_runner import make_retriever
        retriever_fn = make_retriever(container.retriever())
    """
    def _retrieve(artwork_id: str, query: str) -> list[dict]:
        try:
            context_pack = phase2_retriever.retrieve(
                query=query,
                filters={"artwork_id": artwork_id},
            )
            return [
                {"text": chunk.text, "chunk_id": getattr(chunk, "chunk_id", "")}
                for chunk in context_pack.chunks
            ]
        except Exception as exc:
            logger.warning("Retriever error: %s", exc)
            return []
    return _retrieve'''

NEW = '''def make_retriever(phase2_retriever) -> RetrieverFn:
    """
    Wrap a Phase 2 HybridRetriever into the (artwork_id, query) -> list[dict]
    callable that SessionRunner expects.

    The real retriever takes a RetrievalQuery (Pydantic) and returns a
    RetrievalResult with .chunks (each a RetrievedChunk with .text/.chunk_id).
    Only `text` is required on the query; language is mapped from the
    transcript, everything else uses sensible defaults.

    Usage in dependency_container.py:
        from atlas.pipeline.session_runner import make_retriever
        retriever_fn = make_retriever(container.retriever)
    """
    from atlas.rag.retriever import RetrievalQuery
    from atlas.models.enums import Language

    def _lang(code: str) -> Language:
        try:
            return Language(str(code).lower())
        except ValueError:
            return Language.EN

    def _retrieve(artwork_id: str, query: str, language: str = "en") -> list[dict]:
        try:
            rq = RetrievalQuery(
                text=query,
                artwork_id=artwork_id,
                language=_lang(language),
            )
            result = phase2_retriever.retrieve(rq)
            return [
                {"text": chunk.text, "chunk_id": getattr(chunk, "chunk_id", "")}
                for chunk in result.chunks
            ]
        except Exception as exc:
            logger.warning("Retriever error: %s", exc)
            return []
    return _retrieve'''

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

if OLD in text:
    with io.open(PATH + ".bak2", "w", encoding="utf-8") as f:
        f.write(text)
    text = text.replace(OLD, NEW)
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("PATCHED:", PATH, "(backup at " + PATH + ".bak2)")
else:
    print("NOT FOUND - the make_retriever block did not match exactly.")
    print("Paste this output back and do not run anything else.")

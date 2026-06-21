from src.tdd_harness.context import Context, ContextBuilder, ContextType


def test_get_list_tokens():
    builder = ContextBuilder()
    builder.clear()
    builder.add_context(Context(text="A", context_type=ContextType.SYSTEM, token_count=10))
    builder.add_context(Context(text="B", context_type=ContextType.TASK_CONTEXT, token_count=20))
    builder.add_context(Context(text="C", context_type=ContextType.SYSTEM, token_count=15))

    assert builder.get_list_tokens([ContextType.SYSTEM]) == 25
    assert builder.get_list_tokens([ContextType.TASK_CONTEXT]) == 20
    assert builder.get_list_tokens([ContextType.SYSTEM, ContextType.TASK_CONTEXT]) == 45


def test_replace_with_summary():
    builder = ContextBuilder()
    builder.clear()
    c1 = Context(text="Error 1", context_type=ContextType.TRACEBACK, token_count=100)
    c2 = Context(text="Error 2", context_type=ContextType.TRACEBACK, token_count=100)
    builder.add_context(c1)
    builder.add_context(c2)

    builder.replace_with_summary([c1.id, c2.id], "Summary text")

    # The stack should now contain 1 item: the POST_MORTEM_SUMMARY
    assert len(builder.get_context()) == 1
    summary_context = builder.get_context()[0]
    assert summary_context.context_type == ContextType.POST_MORTEM_SUMMARY
    assert summary_context.text == "Summary text"
    assert summary_context.token_count == len("Summary text") // 4

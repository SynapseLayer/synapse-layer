"""Tests for the remember wrapper."""

import pytest
from synapse_memory import SynapseMemory
from synapse_memory.wrapper import remember


@pytest.fixture
def mem():
    return SynapseMemory(agent_id="wrapper-test")


class TestRememberWrapper:
    @pytest.mark.asyncio
    async def test_basic_roundtrip(self, mem):
        @remember(mem, auto_store=True, top_k=3)
        async def greet(prompt: str) -> str:
            return f"Hello from: {prompt}"

        result = await greet("test prompt")
        assert "Hello from:" in result

    @pytest.mark.asyncio
    async def test_auto_store(self, mem):
        @remember(mem, auto_store=True)
        async def produce(text: str) -> str:
            return "User likes blue"

        await produce("color preference")
        # Second call should recall the stored memory
        recalls = await mem.recall("blue")
        assert len(recalls) >= 1

    @pytest.mark.asyncio
    async def test_no_auto_store(self, mem):
        @remember(mem, auto_store=False)
        async def produce(text: str) -> str:
            return "ephemeral output"

        await produce("test")
        recalls = await mem.recall("ephemeral")
        assert len(recalls) == 0

    @pytest.mark.asyncio
    async def test_context_injection(self, mem):
        # Pre-store a memory
        await mem.store("User prefers Python over Java")

        captured_args = []

        @remember(mem, inject_context=True, top_k=3)
        async def process(prompt: str) -> str:
            captured_args.append(prompt)
            return "processed"

        await process("What language does the user prefer?")
        assert "[Recalled context]" in captured_args[0]
        assert "Python" in captured_args[0]

    @pytest.mark.asyncio
    async def test_no_context_injection(self, mem):
        await mem.store("background info")

        captured_args = []

        @remember(mem, inject_context=False)
        async def process(prompt: str) -> str:
            captured_args.append(prompt)
            return "done"

        await process("test query")
        assert "[Recalled context]" not in captured_args[0]

    @pytest.mark.asyncio
    async def test_none_result_not_stored(self, mem):
        @remember(mem, auto_store=True)
        async def void_fn(text: str) -> None:
            return None

        await void_fn("test")
        # Nothing should be stored
        assert len(mem._memories) == 0

    @pytest.mark.asyncio
    async def test_preserves_function_name(self, mem):
        @remember(mem)
        async def my_special_fn(x: str) -> str:
            return x

        assert my_special_fn.__name__ == "my_special_fn"

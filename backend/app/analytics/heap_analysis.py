"""Heap-based Top-N analysis (DSA component).

Two complementary implementations:

1. ``MaxHeap``      — a from-scratch binary max-heap on (amount, expense).
2. ``top_n_expenses`` — an efficient O(n log k) top-k selector built on the
   standard library's ``heapq`` min-heap (explicitly *not* a plain sorted()).
"""

import heapq
from decimal import Decimal
from typing import Any

from backend.app.models.expense import Expense


class MaxHeap:
    """A binary max-heap keyed on ``amount`` (Decimal), ties broken by insertion order.

    Supports push, pop (extract-max), peek, and length. Amounts are compared as
    Decimals; comparison never converts money to float.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[Decimal, int, Any]] = []
        self._counter = 0  # tie-breaker: later items rank lower

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return not self._heap

    def peek(self) -> Any | None:
        """Return the largest item without removing it."""
        return self._heap[0][2] if self._heap else None

    def push(self, amount: Decimal, item: Any) -> None:
        """Insert an item with the given amount; O(log n)."""
        self._counter += 1
        self._heap.append((amount, self._counter, item))
        self._sift_up(len(self._heap) - 1)

    def pop(self) -> Any | None:
        """Remove and return the largest item; O(log n)."""
        if not self._heap:
            return None
        self._swap(0, len(self._heap) - 1)
        _, _, item = self._heap.pop()
        if self._heap:
            self._sift_down(0)
        return item

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, index: int) -> None:
        heap = self._heap
        while index > 0:
            parent = (index - 1) // 2
            if heap[index][0] > heap[parent][0]:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index: int) -> None:
        heap = self._heap
        size = len(heap)
        while True:
            largest = index
            left, right = 2 * index + 1, 2 * index + 2
            if left < size and heap[left][0] > heap[largest][0]:
                largest = left
            if right < size and heap[right][0] > heap[largest][0]:
                largest = right
            if largest == index:
                return
            self._swap(index, largest)
            index = largest


def top_n_expenses_heap_class(expenses: list[Expense], n: int) -> list[Expense]:
    """Top-N expenses via the custom MaxHeap: O(n log n).

    Pops the max repeatedly to produce a descending-order list.
    """
    heap: MaxHeap = MaxHeap()
    for expense in expenses:
        heap.push(Decimal(expense.amount), expense)

    result: list[Expense] = []
    while len(result) < n and not heap.is_empty():
        item = heap.pop()
        if item is not None:
            result.append(item)
    return result


def top_n_expenses(expenses: list[Expense], n: int) -> list[Expense]:
    """Top-N expenses in O(n log k) using heapq as a bounded min-heap.

    The min-heap always holds the current k largest items; the root is the
    smallest of those and is evicted when a larger expense arrives.
    """
    if n <= 0 or not expenses:
        return []

    # (amount, counter, expense): counter keeps tuple comparison stable/valid
    heap: list[tuple[Decimal, int, Expense]] = []
    counter = 0
    for expense in expenses:
        amount = Decimal(expense.amount)
        if len(heap) < n:
            heapq.heappush(heap, (amount, counter, expense))
            counter += 1
        elif amount > heap[0][0]:
            heapq.heapreplace(heap, (amount, counter, expense))
            counter += 1

    # Extract in ascending order, then reverse for descending output.
    ordered: list[Expense] = []
    while heap:
        _, _, expense = heapq.heappop(heap)
        ordered.append(expense)
    ordered.reverse()
    return ordered

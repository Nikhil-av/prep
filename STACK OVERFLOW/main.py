from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
#                        ENUMS
# ═══════════════════════════════════════════════════════════════

class VoteType(Enum):
    UPVOTE = 1
    DOWNVOTE = -1

class QuestionStatus(Enum):
    OPEN = 1
    CLOSED = 2


# ═══════════════════════════════════════════════════════════════
#                     CORE ENTITIES
# ═══════════════════════════════════════════════════════════════

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.reputation = 0
        self.questions: list['Question'] = []
        self.answers: list['Answer'] = []

    def add_reputation(self, points: int):
        self.reputation += points

    def __str__(self):
        return f"👤 {self.name} (Rep: {self.reputation})"


class Comment:
    _counter = 0

    def __init__(self, author: User, body: str):
        Comment._counter += 1
        self.comment_id = Comment._counter
        self.author = author
        self.body = body
        self.created_at = datetime.now()

    def __str__(self):
        return f"💬 {self.author.name}: \"{self.body}\""


class Voteable(ABC):
    """Abstract base — both Question and Answer can be voted on.
    
    WHY: Avoids duplicating vote logic in Question AND Answer.
    Stores votes as dict[user_id → VoteType] to prevent double-voting.
    """
    def __init__(self):
        self.votes: dict[int, VoteType] = {}   # user_id → VoteType
        self.comments: list[Comment] = []

    def vote(self, user: User, vote_type: VoteType):
        """Vote or change existing vote. Prevents self-voting."""
        if user.user_id == self.author.user_id:
            print(f"   ❌ Can't vote on your own post!")
            return

        old_vote = self.votes.get(user.user_id)

        # If same vote exists, remove it (toggle off)
        if old_vote == vote_type:
            del self.votes[user.user_id]
            self._update_reputation(vote_type, undo=True)
            print(f"   🔄 {user.name} removed {vote_type.name}")
            return

        # If opposite vote exists, undo it first
        if old_vote is not None:
            self._update_reputation(old_vote, undo=True)

        # Apply new vote
        self.votes[user.user_id] = vote_type
        self._update_reputation(vote_type, undo=False)
        print(f"   {'👍' if vote_type == VoteType.UPVOTE else '👎'} {user.name} {vote_type.name.lower()}d")

    @abstractmethod
    def _update_reputation(self, vote_type: VoteType, undo: bool):
        """Each subclass defines reputation rules."""
        pass

    def get_vote_count(self) -> int:
        return sum(v.value for v in self.votes.values())

    def add_comment(self, user: User, body: str) -> Comment:
        comment = Comment(user, body)
        self.comments.append(comment)
        return comment


class Question(Voteable):
    """
    Reputation rules:
        Upvote   → author gets +5
        Downvote → author gets -2
    """
    _counter = 0

    def __init__(self, author: User, title: str, body: str, tags: list[str]):
        super().__init__()
        Question._counter += 1
        self.question_id = Question._counter
        self.author = author
        self.title = title
        self.body = body
        self.tags = tags
        self.answers: list['Answer'] = []
        self.accepted_answer: 'Answer | None' = None
        self.status = QuestionStatus.OPEN
        self.created_at = datetime.now()

    def _update_reputation(self, vote_type: VoteType, undo: bool):
        multiplier = -1 if undo else 1
        if vote_type == VoteType.UPVOTE:
            self.author.add_reputation(5 * multiplier)
        else:
            self.author.add_reputation(-2 * multiplier)

    def accept_answer(self, answer: 'Answer', user: User):
        """Only question author can accept an answer."""
        if user.user_id != self.author.user_id:
            print(f"   ❌ Only the question author can accept answers!")
            return
        if answer not in self.answers:
            print(f"   ❌ This answer doesn't belong to this question!")
            return

        # Undo previous acceptance
        if self.accepted_answer:
            self.accepted_answer.is_accepted = False
            self.accepted_answer.author.add_reputation(-15)

        self.accepted_answer = answer
        answer.is_accepted = True
        answer.author.add_reputation(15)  # +15 for accepted answer
        print(f"   ✅ {self.author.name} accepted {answer.author.name}'s answer (+15 rep)")

    def __str__(self):
        tags_str = ", ".join(self.tags)
        return (f"❓ Q#{self.question_id}: \"{self.title}\" "
                f"[{tags_str}] by {self.author.name} | "
                f"Score: {self.get_vote_count()} | "
                f"Answers: {len(self.answers)} | "
                f"{'✅ Accepted' if self.accepted_answer else '⏳ Open'}")


class Answer(Voteable):
    """
    Reputation rules:
        Upvote   → author gets +10
        Downvote → author gets -2 (voter gets -1)
        Accepted → author gets +15
    """
    _counter = 0

    def __init__(self, author: User, question: Question, body: str):
        super().__init__()
        Answer._counter += 1
        self.answer_id = Answer._counter
        self.author = author
        self.question = question
        self.body = body
        self.is_accepted = False
        self.created_at = datetime.now()

    def _update_reputation(self, vote_type: VoteType, undo: bool):
        multiplier = -1 if undo else 1
        if vote_type == VoteType.UPVOTE:
            self.author.add_reputation(10 * multiplier)
        else:
            self.author.add_reputation(-2 * multiplier)

    def __str__(self):
        accepted = "✅" if self.is_accepted else "  "
        return (f"   {accepted} A#{self.answer_id}: \"{self.body[:50]}...\" "
                f"by {self.author.name} | Score: {self.get_vote_count()}")


class Tag:
    def __init__(self, name: str):
        self.name = name.lower()
        self.questions: list[Question] = []

    def __str__(self):
        return f"🏷️ {self.name} ({len(self.questions)} questions)"


# ═══════════════════════════════════════════════════════════════
#                     SEARCH STRATEGIES
# ═══════════════════════════════════════════════════════════════

class SearchStrategy(ABC):
    @abstractmethod
    def search(self, query: str, questions: list[Question]) -> list[Question]:
        pass

class SearchByKeyword(SearchStrategy):
    def search(self, query: str, questions: list[Question]) -> list[Question]:
        q = query.lower()
        return [qn for qn in questions
                if q in qn.title.lower() or q in qn.body.lower()]

class SearchByTag(SearchStrategy):
    def search(self, query: str, questions: list[Question]) -> list[Question]:
        q = query.lower()
        return [qn for qn in questions if q in [t.lower() for t in qn.tags]]

class SearchByUser(SearchStrategy):
    def search(self, query: str, questions: list[Question]) -> list[Question]:
        q = query.lower()
        return [qn for qn in questions if q in qn.author.name.lower()]


# ═══════════════════════════════════════════════════════════════
#              STACK OVERFLOW SYSTEM (SINGLETON)
# ═══════════════════════════════════════════════════════════════

class StackOverflow:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.users: dict[int, User] = {}
        self.questions: dict[int, Question] = {}
        self.tags: dict[str, Tag] = {}

    # ─── Users ───
    def register_user(self, user_id: int, name: str, email: str) -> User:
        user = User(user_id, name, email)
        self.users[user_id] = user
        return user

    # ─── Questions ───
    def post_question(self, user_id: int, title: str, body: str, tags: list[str]) -> Question:
        user = self.users.get(user_id)
        if not user:
            print("   ❌ User not found!")
            return None

        question = Question(user, title, body, tags)
        self.questions[question.question_id] = question
        user.questions.append(question)

        # Register tags
        for tag_name in tags:
            tag_key = tag_name.lower()
            if tag_key not in self.tags:
                self.tags[tag_key] = Tag(tag_key)
            self.tags[tag_key].questions.append(question)

        print(f"   📝 Q#{question.question_id}: \"{title}\" posted by {user.name}")
        return question

    # ─── Answers ───
    def post_answer(self, user_id: int, question_id: int, body: str) -> Answer:
        user = self.users.get(user_id)
        question = self.questions.get(question_id)
        if not user or not question:
            print("   ❌ User or Question not found!")
            return None

        answer = Answer(user, question, body)
        question.answers.append(answer)
        user.answers.append(answer)
        print(f"   💡 A#{answer.answer_id}: {user.name} answered Q#{question_id}")
        return answer

    # ─── Comments ───
    def add_comment(self, user_id: int, target: Voteable, body: str) -> Comment:
        user = self.users.get(user_id)
        if not user:
            print("   ❌ User not found!")
            return None
        comment = target.add_comment(user, body)
        print(f"   {comment}")
        return comment

    # ─── Voting ───
    def vote_question(self, user_id: int, question_id: int, vote_type: VoteType):
        user = self.users.get(user_id)
        question = self.questions.get(question_id)
        if user and question:
            question.vote(user, vote_type)

    def vote_answer(self, user_id: int, answer: Answer, vote_type: VoteType):
        user = self.users.get(user_id)
        if user and answer:
            answer.vote(user, vote_type)

    # ─── Accept Answer ───
    def accept_answer(self, user_id: int, question_id: int, answer: Answer):
        user = self.users.get(user_id)
        question = self.questions.get(question_id)
        if user and question:
            question.accept_answer(answer, user)

    # ─── Search ───
    def search(self, query: str, strategy: SearchStrategy) -> list[Question]:
        return strategy.search(query, list(self.questions.values()))


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("         STACK OVERFLOW - LLD DEMO")
    print("=" * 65)

    so = StackOverflow()

    # ─── Register Users ───
    print("\n👥 Registering Users:")
    u1 = so.register_user(1, "Nikhil", "nikhil@gmail.com")
    u2 = so.register_user(2, "Priya", "priya@gmail.com")
    u3 = so.register_user(3, "Rahul", "rahul@gmail.com")
    for u in [u1, u2, u3]:
        print(f"   {u}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 1: Post Question + Answers
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 1: Post Question + Answers")
    print("─" * 65)

    print("\n① Nikhil posts a question:")
    q1 = so.post_question(1, "How to implement Singleton in Python?",
                          "What's the best way to implement Singleton pattern in Python?",
                          ["python", "design-patterns", "singleton"])

    print("\n② Priya answers:")
    a1 = so.post_answer(2, q1.question_id,
                        "Use __new__ method with a class variable _instance. Check if None, create if needed, always return _instance.")

    print("\n③ Rahul also answers:")
    a2 = so.post_answer(3, q1.question_id,
                        "Use a metaclass or a module-level variable. Metaclass approach is cleaner for complex singletons.")

    # ═══════════════════════════════════════════════════════════
    #  TEST 2: Voting
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 2: Voting + Reputation")
    print("─" * 65)

    print(f"\n   Before voting: {u1} | {u2} | {u3}")

    print("\n① Priya upvotes Nikhil's question (+5 to Nikhil):")
    so.vote_question(2, q1.question_id, VoteType.UPVOTE)

    print("\n② Rahul upvotes Nikhil's question (+5 to Nikhil):")
    so.vote_question(3, q1.question_id, VoteType.UPVOTE)

    print("\n③ Nikhil upvotes Priya's answer (+10 to Priya):")
    so.vote_answer(1, a1, VoteType.UPVOTE)

    print("\n④ Nikhil upvotes Rahul's answer (+10 to Rahul):")
    so.vote_answer(1, a2, VoteType.UPVOTE)

    print("\n⑤ Priya tries to upvote her own answer (should fail):")
    so.vote_answer(2, a1, VoteType.UPVOTE)

    print(f"\n   After voting: {u1} | {u2} | {u3}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 3: Accept Answer
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 3: Accept Answer")
    print("─" * 65)

    print("\n① Nikhil accepts Priya's answer (+15 to Priya):")
    so.accept_answer(1, q1.question_id, a1)

    print(f"\n   After accept: {u2}")

    print("\n② Rahul tries to accept (not question author — should fail):")
    so.accept_answer(3, q1.question_id, a2)

    # ═══════════════════════════════════════════════════════════
    #  TEST 4: Comments
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 4: Comments")
    print("─" * 65)

    print("\n① Comment on question:")
    so.add_comment(2, q1, "Great question! I was confused about this too.")

    print("\n② Comment on answer:")
    so.add_comment(1, a1, "Thanks! The __new__ approach is exactly what I needed.")

    # ═══════════════════════════════════════════════════════════
    #  TEST 5: Search
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 5: Search")
    print("─" * 65)

    # Post another question for search testing
    q2 = so.post_question(2, "What is Observer pattern in Java?",
                          "How to implement Observer pattern?",
                          ["java", "design-patterns", "observer"])

    print("\n🔍 Search by keyword 'singleton':")
    results = so.search("singleton", SearchByKeyword())
    for r in results:
        print(f"   {r}")

    print("\n🔍 Search by tag 'design-patterns':")
    results = so.search("design-patterns", SearchByTag())
    for r in results:
        print(f"   {r}")

    print("\n🔍 Search by user 'nikhil':")
    results = so.search("nikhil", SearchByUser())
    for r in results:
        print(f"   {r}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 6: Vote Toggle (undo vote)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 6: Vote Toggle")
    print("─" * 65)

    print(f"\n   Priya's rep before undo: {u2.reputation}")
    print("① Nikhil removes upvote on Priya's answer (upvote again = toggle):")
    so.vote_answer(1, a1, VoteType.UPVOTE)
    print(f"   Priya's rep after undo: {u2.reputation}")

    # ═══════════════════════════════════════════════════════════
    #  FINAL STATE
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  FINAL STATE")
    print("─" * 65)

    print("\n📊 Users:")
    for u in so.users.values():
        print(f"   {u}")

    print("\n📊 Questions:")
    for q in so.questions.values():
        print(f"   {q}")
        for a in q.answers:
            print(f"   {a}")

    print("\n📊 Tags:")
    for t in so.tags.values():
        print(f"   {t}")

    print(f"\n🔒 Singleton: {so is StackOverflow()} ✓")

    print("\n" + "=" * 65)
    print("         ALL TESTS COMPLETE! 🎉")
    print("=" * 65)

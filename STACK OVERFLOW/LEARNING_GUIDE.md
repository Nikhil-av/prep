# 💬 STACK OVERFLOW — Q&A Platform LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Stack Overflow-like Q&A platform**. Users post questions, answer them, vote, comment, and earn reputation.

---

## 🤔 THINK: Before Reading Further...
**What makes this problem unique compared to other LLD problems?**

<details>
<summary>👀 Click to reveal</summary>

This problem is about **deep OOP hierarchy and shared behavior**:
- Questions and Answers BOTH support voting → **abstract base class (Voteable)**
- Questions and Answers BOTH support comments → shared via Voteable or composition
- Reputation is earned through actions across entities → cross-entity side effects
- Vote toggling (vote again = undo) → tricky state management

No state machine, no concurrency challenges — pure **entity design and inheritance**.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Post questions with title, body, tags |
| 2 | Post answers to questions |
| 3 | Comment on questions and answers |
| 4 | **Upvote/downvote** on questions and answers |
| 5 | **Accept answer** — only question author can |
| 6 | **Reputation system** — earned/lost through votes |
| 7 | Search — by keyword, by tag, by user |
| 8 | Prevent self-voting, support vote toggling |

---

## 🔥 THE KEY INSIGHT: Voteable Abstract Base Class

### 🤔 THINK: Both Questions and Answers can be voted on. How do you avoid duplicating voting logic?

<details>
<summary>👀 Click to reveal</summary>

**Extract shared voting into an ABC:**
```python
class Voteable(ABC):
    def __init__(self):
        self.votes: dict[int, VoteType] = {}  # {user_id: UPVOTE/DOWNVOTE}
    
    def vote(self, user, vote_type):
        if user.user_id == self.author.user_id:
            return "Can't vote on own post!"
        
        old_vote = self.votes.get(user.user_id)
        
        if old_vote == vote_type:      # Same vote → toggle OFF
            del self.votes[user.user_id]
            self._update_reputation(vote_type, undo=True)
        else:
            if old_vote:               # Different vote → undo old first
                self._update_reputation(old_vote, undo=True)
            self.votes[user.user_id] = vote_type
            self._update_reputation(vote_type, undo=False)
    
    @abstractmethod
    def _update_reputation(self, vote_type, undo): pass

class Question(Voteable):
    def _update_reputation(self, vote_type, undo):
        mult = -1 if undo else 1
        if vote_type == VoteType.UPVOTE: self.author.reputation += 5 * mult
        else: self.author.reputation += -2 * mult

class Answer(Voteable):
    def _update_reputation(self, vote_type, undo):
        mult = -1 if undo else 1
        if vote_type == VoteType.UPVOTE: self.author.reputation += 10 * mult
        else: self.author.reputation += -2 * mult
```

**Why `dict[user_id, VoteType]` for votes?**
- O(1) lookup for "has this user already voted?"
- Easy toggle (delete entry to undo)
- Prevents double voting
- One user = one vote per post

</details>

---

## 💰 Reputation System

### 🤔 THINK: What actions affect reputation and by how much?

<details>
<summary>👀 Click to reveal</summary>

| Action | Whose Reputation? | Change |
|--------|--------------------|--------|
| Question upvoted | Question author | **+5** |
| Question downvoted | Question author | **-2** |
| Answer upvoted | Answer author | **+10** |
| Answer downvoted | Answer author | **-2** |
| Answer accepted | Answer author | **+15** |
| Upvote removed (toggle) | Undo the above | Reverse |

**Why different values?** Answers require more effort than questions → higher reward. Accepted answer is the BEST answer → highest reward.

</details>

---

## 📊 Accept Answer Flow

### 🤔 THINK: What happens if the author accepts Answer A, then later accepts Answer B?

<details>
<summary>👀 Click to reveal</summary>

```python
def accept_answer(self, answer, user):
    if user != self.author:
        return "Only author can accept!"
    
    # Undo previous acceptance
    if self.accepted_answer:
        self.accepted_answer.is_accepted = False
        self.accepted_answer.author.reputation -= 15  # Take back!
    
    # Accept new answer
    self.accepted_answer = answer
    answer.is_accepted = True
    answer.author.reputation += 15
```

**Key:** Only ONE accepted answer per question. Re-accepting undoes the previous.

</details>

---

## 🔗 Entity Relationships

```
StackOverflow (Singleton)
    ├── users: dict[id, User]
    ├── questions: dict[id, Question]
    └── tags: dict[name, Tag]

User
    ├── questions: list[Question]
    ├── answers: list[Answer]
    └── reputation: int

Question (extends Voteable)
    ├── author: User
    ├── answers: list[Answer]
    ├── comments: list[Comment]
    ├── tags: list[str]
    └── accepted_answer: Answer | None

Answer (extends Voteable)
    ├── author: User
    ├── question: Question
    ├── comments: list[Comment]
    └── is_accepted: bool

Tag
    └── questions: list[Question]
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Template Method / ABC** | Voteable → Question, Answer | Shared vote logic, different reputation rules |
| **Strategy** | SearchStrategy (keyword, tag, user) | Interchangeable search algorithms |
| **Singleton** | StackOverflow | One system |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to implement a bounty system?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Bounty:
    def __init__(self, question, amount, expires_at):
        self.question = question
        self.amount = amount  # From author's reputation
        self.expires_at = expires_at
        question.author.reputation -= amount  # Deducted upfront
    
    def award(self, answer):
        answer.author.reputation += self.amount
```
Author puts up reputation as bounty → awarded to best answer.

</details>

### Q2: "How to sort answers? (e.g., highest voted first, accepted first)"

<details>
<summary>👀 Click to reveal</summary>

```python
def get_sorted_answers(self):
    return sorted(self.answers, 
                  key=lambda a: (a.is_accepted, a.get_vote_count()), 
                  reverse=True)
```
Accepted answer always on top, then by vote count.

</details>

### Q3: "How to prevent abuse (spam, vote brigading)?"

<details>
<summary>👀 Click to reveal</summary>

- **Rate limiting**: Max N questions/answers per day per user
- **Min reputation to downvote**: User needs 125+ rep to downvote
- **Serial voting detection**: If user A votes on 5 of user B's posts in 1 min → flag
- **Spam filter**: Duplicate detection, keyword blacklist

</details>

### Q4: "How to implement question closing/reopening?"

<details>
<summary>👀 Click to reveal</summary>

```python
class QuestionStatus(Enum):
    OPEN = 1
    CLOSED = 2

class CloseVote:
    reason: str  # "Duplicate", "Off-topic", etc.
    user: User

class Question:
    close_votes: list[CloseVote]
    
    def try_close(self):
        if len(self.close_votes) >= 5:  # 5 votes to close
            self.status = QuestionStatus.CLOSED
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "The key design choice is the **Voteable abstract base class** shared by Question and Answer — it handles vote storage, toggling, and self-vote prevention. Each subclass implements `_update_reputation()` with different point values. Votes are stored as `dict[user_id → VoteType]` for O(1) lookup and toggle support. Only the question author can accept one answer (+15 rep). I use **Strategy pattern** for search (keyword, tag, user) and **Singleton** for the system."

---

## ✅ Pre-Implementation Checklist

- [ ] VoteType enum (UPVOTE=1, DOWNVOTE=-1)
- [ ] Voteable ABC with vote(), toggle, self-vote prevention
- [ ] Question extends Voteable (+5/-2 reputation)
- [ ] Answer extends Voteable (+10/-2 reputation, +15 accepted)
- [ ] Comment (simple, no voting)
- [ ] Tag with question list
- [ ] User with reputation tracking
- [ ] Accept answer (only author, undo previous)
- [ ] SearchStrategy (keyword, tag, user)
- [ ] StackOverflow singleton
- [ ] Demo: post, vote, toggle vote, accept, search

---

*Document created during LLD interview prep session*

# 🎓 COURSERA — Online Learning Platform LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **Online Learning Platform** like Coursera/Udemy. Instructors create courses with modules and lessons, students enroll, track progress, and earn certificates.

---

## 🤔 THINK: Before Reading Further...
**What's the entity hierarchy? Think about it like a book with chapters.**

<details>
<summary>👀 Click to reveal</summary>

```
Course → Module → Lesson
(Book)   (Chapter)  (Page)
```

A Course has multiple Modules, each Module has multiple Lessons. Progress is tracked at the Lesson level.

| Entity | Example |
|--------|---------|
| **Course** | "Python for Beginners" |
| **Module** | "Variables & Data Types" |
| **Lesson** | "What are Strings?" (video/text) |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | **Instructors** create courses with modules and lessons |
| 2 | **Students** browse and **enroll** in courses |
| 3 | **Track progress** — mark lessons as complete |
| 4 | **Search** courses by title, category, instructor |
| 5 | **Certificate** on course completion |
| 6 | **Rating & reviews** for courses |
| 7 | Payment for paid courses |

---

## 🔥 THE KEY INSIGHT: Progress Tracking

### 🤔 THINK: How do you track a student's progress across a course with 5 modules and 20 lessons?

<details>
<summary>👀 Click to reveal</summary>

**Enrollment links Student to Course. Progress tracked per lesson:**

```python
class Enrollment:
    student: Student
    course: Course
    completed_lessons: set[int]    # lesson_ids
    enrolled_at: datetime
    completed_at: datetime | None
    certificate: Certificate | None
    
    def complete_lesson(self, lesson_id):
        self.completed_lessons.add(lesson_id)
        total = self.course.total_lessons()
        if len(self.completed_lessons) == total:
            self.completed_at = datetime.now()
            self.certificate = Certificate(self)
            print("🎉 Course completed! Certificate issued!")
    
    def progress_percentage(self):
        return len(self.completed_lessons) / self.course.total_lessons() * 100
```

**Why `set` for completed lessons?** O(1) lookup, prevents double-marking.

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal</summary>

| Entity | Key Attributes |
|--------|---------------|
| **LessonType** | VIDEO, TEXT, QUIZ |
| **Lesson** | id, title, content, type, duration |
| **Module** | id, title, lessons[] |
| **Course** | id, title, instructor, modules[], price, rating |
| **Student** | id, name, enrollments[] |
| **Instructor** | id, name, courses[] |
| **Enrollment** | student, course, completed_lessons, certificate |
| **Certificate** | id, student, course, issued_at |
| **Review** | student, course, rating, comment |
| **CoursePlatform (Singleton)** | courses, students, instructors |

</details>

---

## 🔗 Entity Relationships

```
CoursePlatform (Singleton)
    ├── instructors: dict[id, Instructor]
    ├── students: dict[id, Student]
    └── courses: dict[id, Course]

Course
    ├── instructor: Instructor
    ├── modules: list[Module]
    │     └── lessons: list[Lesson]
    └── reviews: list[Review]

Student
    └── enrollments: list[Enrollment]
          ├── course: Course
          ├── completed_lessons: set
          └── certificate: Certificate | None
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to add prerequisites (must complete Course A before Course B)?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Course:
    prerequisites: list[Course]

def enroll(self, student, course):
    for prereq in course.prerequisites:
        if not self._has_completed(student, prereq):
            return f"Must complete {prereq.title} first!"
    # ... proceed with enrollment
```

</details>

### Q2: "How to support quizzes with grading?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Quiz(Lesson):
    questions: list[Question]
    passing_score: float
    
    def submit(self, answers: dict[int, str]) -> float:
        correct = sum(1 for q in self.questions
                     if answers.get(q.id) == q.correct_answer)
        score = correct / len(self.questions) * 100
        return score  # Must >= passing_score to complete
```

</details>

### Q3: "How to add a recommendation system?"

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern:**
```python
class RecommendationStrategy(ABC):
    def recommend(self, student) -> list[Course]: pass

class CategoryBased(RecommendationStrategy):
    def recommend(self, student):
        # Find categories of completed courses
        # Return popular courses in same categories
        pass

class CollaborativeFiltering(RecommendationStrategy):
    def recommend(self, student):
        # Students who took X also took Y
        pass
```

</details>

### Q4: "How to handle free vs paid courses?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Course:
    price: float  # 0 = free
    
    def is_free(self): return self.price == 0

def enroll(self, student, course, payment=None):
    if not course.is_free():
        if not payment:
            return "Payment required!"
        payment.pay(course.price)
    # ... create enrollment
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd model it as **Course → Module → Lesson** hierarchy. Progress is tracked via **Enrollment** which links Student to Course and stores a `set` of completed lesson IDs. When all lessons are completed, a **Certificate** is auto-generated. Courses can have prerequisites (checked on enrollment). I'd use **Strategy pattern** for search (by title, category) and payment. Ratings are per-course with reviews."

---

## ✅ Pre-Implementation Checklist

- [ ] Lesson (video, text, quiz types)
- [ ] Module (ordered list of lessons)
- [ ] Course (modules, instructor, price, rating)
- [ ] Student with enrollments
- [ ] Enrollment (progress tracking via completed_lessons set)
- [ ] Certificate (auto-generated on completion)
- [ ] Review/Rating
- [ ] SearchStrategy (by title, category, instructor)
- [ ] PaymentStrategy (free vs paid)
- [ ] CoursePlatform singleton
- [ ] Demo: enroll, complete lessons, earn certificate

---

*Document created during LLD interview prep session*

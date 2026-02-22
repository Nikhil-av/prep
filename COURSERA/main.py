from enum import Enum
from datetime import datetime

# ============ ENUMS ============

class EnrollmentStatus(Enum):
    ENROLLED = "ENROLLED"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"

class UserRole(Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"


# ============ QUESTION ============

class Question:
    def __init__(self, question_id: int, text: str, options: list, correct_option: int):
        self.question_id = question_id
        self.text = text
        self.options = options
        self.correct_option = correct_option  # 0-indexed

    def is_correct(self, selected: int) -> bool:
        return selected == self.correct_option

    def __str__(self):
        options_str = ", ".join([f"{i}: {o}" for i, o in enumerate(self.options)])
        return f"Q{self.question_id}: {self.text} [{options_str}]"


# ============ QUIZ (TEST) ============

class Quiz:
    def __init__(self, quiz_id: int, title: str, passing_score: int = 70):
        self.quiz_id = quiz_id
        self.title = title
        self.questions = []
        self.passing_score = passing_score  # Percentage

    def add_question(self, question: Question):
        self.questions.append(question)

    def calculate_score(self, answers: dict) -> float:
        """
        answers: {question_id: selected_option_index}
        Returns: percentage score
        """
        if not self.questions:
            return 0.0
        correct = 0
        for question in self.questions:
            if question.question_id in answers:
                if question.is_correct(answers[question.question_id]):
                    correct += 1
        return (correct / len(self.questions)) * 100

    def is_passed(self, score: float) -> bool:
        return score >= self.passing_score

    def __str__(self):
        return f"Quiz({self.title}, {len(self.questions)} questions, pass: {self.passing_score}%)"


# ============ SUBMODULE (LESSON) ============

class Submodule:
    def __init__(self, submodule_id: int, title: str, order: int):
        self.submodule_id = submodule_id
        self.title = title
        self.order = order
        # Content (all optional)
        self.video_url = None
        self.video_duration = 0  # minutes
        self.text_content = None
        self.quiz = None

    def has_video(self) -> bool:
        return self.video_url is not None

    def has_text(self) -> bool:
        return self.text_content is not None

    def has_quiz(self) -> bool:
        return self.quiz is not None

    def set_video(self, url: str, duration: int):
        self.video_url = url
        self.video_duration = duration

    def set_text(self, text: str):
        self.text_content = text

    def set_quiz(self, quiz: Quiz):
        self.quiz = quiz

    def __str__(self):
        content = []
        if self.has_video():
            content.append(f"Video({self.video_duration}min)")
        if self.has_text():
            content.append("Text")
        if self.has_quiz():
            content.append("Quiz")
        return f"Submodule({self.title}, {', '.join(content) if content else 'Empty'})"


# ============ MODULE ============

class Module:
    def __init__(self, module_id: int, title: str, order: int):
        self.module_id = module_id
        self.title = title
        self.order = order
        self.submodules = []

    def add_submodule(self, submodule: Submodule):
        self.submodules.append(submodule)

    def get_quizzes(self) -> list:
        return [sub.quiz for sub in self.submodules if sub.has_quiz()]

    def __str__(self):
        return f"Module({self.title}, {len(self.submodules)} submodules)"


# ============ USER ============

class User:
    def __init__(self, user_id: int, name: str, email: str, role: UserRole = UserRole.STUDENT):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role

    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    def is_instructor(self) -> bool:
        return self.role == UserRole.INSTRUCTOR

    def __str__(self):
        return f"User({self.name}, {self.role.value})"


# ============ COURSE ============

class Course:
    def __init__(self, course_id: int, title: str, description: str, price: float, instructor: User):
        self.course_id = course_id
        self.title = title
        self.description = description
        self.price = price
        self.instructor = instructor
        self.modules = []

    def add_module(self, module: Module):
        self.modules.append(module)

    def get_all_submodules(self) -> list:
        submodules = []
        for module in self.modules:
            submodules.extend(module.submodules)
        return submodules

    def get_all_quizzes(self) -> list:
        quizzes = []
        for module in self.modules:
            quizzes.extend(module.get_quizzes())
        return quizzes

    def is_free(self) -> bool:
        return self.price == 0

    def __str__(self):
        price_str = "Free" if self.is_free() else f"₹{self.price}"
        return f"Course({self.title}, {price_str}, {len(self.modules)} modules)"


# ============ ENROLLMENT ============

class Enrollment:
    def __init__(self, enrollment_id: int, student: User, course: Course):
        self.enrollment_id = enrollment_id
        self.student = student
        self.course = course
        self.status = EnrollmentStatus.ENROLLED
        self.enrolled_at = datetime.now()
        # Initialize progress tracking
        self.submodule_progress = {}  # submodule_id → bool (completed)
        self.quiz_scores = {}  # quiz_id → best score (float)
        self._initialize_progress()

    def _initialize_progress(self):
        """Initialize progress tracking for all submodules."""
        for submodule in self.course.get_all_submodules():
            self.submodule_progress[submodule.submodule_id] = False

    def mark_submodule_complete(self, submodule_id: int):
        """Mark a submodule as completed."""
        if submodule_id in self.submodule_progress:
            self.submodule_progress[submodule_id] = True
            print(f"✅ Completed submodule {submodule_id}")

    def record_quiz_score(self, quiz_id: int, score: float):
        """Record quiz score (keeps best score)."""
        current_best = self.quiz_scores.get(quiz_id, 0)
        if score > current_best:
            self.quiz_scores[quiz_id] = score
            print(f"📝 New best score for quiz {quiz_id}: {score:.1f}%")
        else:
            print(f"📝 Score {score:.1f}% (best remains {current_best:.1f}%)")

    def get_progress_percent(self) -> float:
        """Calculate overall progress percentage."""
        if not self.submodule_progress:
            return 0.0
        completed = sum(1 for done in self.submodule_progress.values() if done)
        return (completed / len(self.submodule_progress)) * 100

    def is_course_complete(self) -> bool:
        """Check if all submodules done and all quizzes passed."""
        # Check all submodules completed
        all_submodules_done = all(self.submodule_progress.values())
        
        # Check all quizzes passed
        all_quizzes = self.course.get_all_quizzes()
        if not all_quizzes:
            all_quizzes_passed = True
        else:
            all_quizzes_passed = all(
                self.quiz_scores.get(q.quiz_id, 0) >= q.passing_score
                for q in all_quizzes
            )
        
        return all_submodules_done and all_quizzes_passed

    def __str__(self):
        progress = self.get_progress_percent()
        return f"Enrollment({self.student.name} → {self.course.title}, {progress:.0f}%, {self.status.value})"


# ============ CERTIFICATE ============

class Certificate:
    def __init__(self, certificate_id: int, student: User, course: Course):
        self.certificate_id = certificate_id
        self.student = student
        self.course = course
        self.issued_at = datetime.now()

    def generate(self) -> str:
        """Generate certificate as text."""
        separator = "═" * 50
        return f"""
{separator}
            CERTIFICATE OF COMPLETION
{separator}

This certifies that

                {self.student.name.upper()}

has successfully completed

            "{self.course.title}"

Instructor: {self.course.instructor.name}
Date: {self.issued_at.strftime('%Y-%m-%d')}
Certificate ID: {self.certificate_id}

{separator}
"""

    def __str__(self):
        return f"Certificate({self.student.name}, {self.course.title})"


# ============ LEARNING PLATFORM (Singleton Facade) ============

class LearningPlatform:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LearningPlatform, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.users = {}
        self.courses = {}
        self.enrollments = []
        self.certificates = []
        self._user_counter = 0
        self._course_counter = 0
        self._enrollment_counter = 0
        self._certificate_counter = 0

    # ---- User Management ----
    def register_user(self, name: str, email: str, role: UserRole = UserRole.STUDENT) -> User:
        self._user_counter += 1
        user = User(self._user_counter, name, email, role)
        self.users[user.user_id] = user
        print(f"✅ Registered: {user}")
        return user

    def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

    # ---- Course Management ----
    def create_course(self, title: str, description: str, price: float, instructor: User) -> Course:
        if not instructor.is_instructor():
            raise Exception("Only instructors can create courses")
        self._course_counter += 1
        course = Course(self._course_counter, title, description, price, instructor)
        self.courses[course.course_id] = course
        print(f"✅ Created: {course}")
        return course

    def get_course(self, course_id: int) -> Course:
        return self.courses.get(course_id)

    def get_all_courses(self) -> list:
        return list(self.courses.values())

    # ---- Enrollment ----
    def enroll(self, student: User, course: Course) -> Enrollment:
        if not student.is_student():
            raise Exception("Only students can enroll")
        
        # Check if already enrolled
        for e in self.enrollments:
            if e.student.user_id == student.user_id and e.course.course_id == course.course_id:
                raise Exception("Already enrolled in this course")
        
        self._enrollment_counter += 1
        enrollment = Enrollment(self._enrollment_counter, student, course)
        self.enrollments.append(enrollment)
        print(f"✅ Enrolled: {enrollment}")
        return enrollment

    def get_enrollment(self, student: User, course: Course) -> Enrollment:
        for e in self.enrollments:
            if e.student.user_id == student.user_id and e.course.course_id == course.course_id:
                return e
        return None

    # ---- Progress ----
    def complete_submodule(self, enrollment: Enrollment, submodule_id: int):
        enrollment.mark_submodule_complete(submodule_id)
        self._check_completion(enrollment)

    def submit_quiz(self, enrollment: Enrollment, quiz: Quiz, answers: dict) -> float:
        score = quiz.calculate_score(answers)
        passed = quiz.is_passed(score)
        enrollment.record_quiz_score(quiz.quiz_id, score)
        
        status = "PASSED ✅" if passed else "FAILED ❌"
        print(f"Quiz '{quiz.title}': {score:.1f}% - {status}")
        
        self._check_completion(enrollment)
        return score

    def _check_completion(self, enrollment: Enrollment):
        if enrollment.is_course_complete() and enrollment.status != EnrollmentStatus.COMPLETED:
            enrollment.status = EnrollmentStatus.COMPLETED
            certificate = self._issue_certificate(enrollment)
            print(f"🎓 Course completed! Certificate issued.")
            print(certificate.generate())

    def _issue_certificate(self, enrollment: Enrollment) -> Certificate:
        self._certificate_counter += 1
        certificate = Certificate(
            self._certificate_counter,
            enrollment.student,
            enrollment.course
        )
        self.certificates.append(certificate)
        return certificate


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("ONLINE LEARNING PLATFORM - DEMO")
    print("=" * 60)

    # Get platform instance
    platform = LearningPlatform()

    # 1. Register users
    print("\n--- 1. Register Users ---")
    instructor = platform.register_user("John Doe", "john@instructor.com", UserRole.INSTRUCTOR)
    student = platform.register_user("Nikhil", "nikhil@student.com", UserRole.STUDENT)

    # 2. Create a course
    print("\n--- 2. Create Course ---")
    course = platform.create_course(
        title="Python Masterclass",
        description="Learn Python from scratch",
        price=999,
        instructor=instructor
    )

    # 3. Add modules
    print("\n--- 3. Add Modules & Submodules ---")
    
    # Module 1: Introduction
    module1 = Module(1, "Introduction", order=1)
    
    sub1 = Submodule(1, "Welcome to Python", order=1)
    sub1.set_video("https://youtube.com/python-welcome", 10)
    sub1.set_text("Python is a versatile programming language...")
    
    sub2 = Submodule(2, "Setting Up Environment", order=2)
    sub2.set_video("https://youtube.com/python-setup", 15)
    sub2.set_text("Download Python from python.org...")
    
    module1.add_submodule(sub1)
    module1.add_submodule(sub2)
    
    # Module 2: Basics
    module2 = Module(2, "Python Basics", order=2)
    
    sub3 = Submodule(3, "Variables and Data Types", order=1)
    sub3.set_video("https://youtube.com/python-variables", 20)
    sub3.set_text("Variables store data in memory...")
    
    # Add quiz to this submodule
    quiz = Quiz(1, "Variables Quiz", passing_score=70)
    quiz.add_question(Question(1, "What is a variable?", 
        ["A container for data", "A function", "A loop", "An error"], 0))
    quiz.add_question(Question(2, "Which is a valid variable name?",
        ["1name", "my-var", "my_var", "class"], 2))
    quiz.add_question(Question(3, "What type is 3.14?",
        ["int", "str", "float", "bool"], 2))
    sub3.set_quiz(quiz)
    
    module2.add_submodule(sub3)
    
    course.add_module(module1)
    course.add_module(module2)
    
    print(f"Added: {module1}")
    print(f"Added: {module2}")
    print(f"Total submodules: {len(course.get_all_submodules())}")
    print(f"Total quizzes: {len(course.get_all_quizzes())}")

    # 4. Student enrolls
    print("\n--- 4. Student Enrolls ---")
    enrollment = platform.enroll(student, course)
    print(f"Progress: {enrollment.get_progress_percent():.0f}%")

    # 5. Student watches content
    print("\n--- 5. Student Completes Submodules ---")
    platform.complete_submodule(enrollment, 1)
    platform.complete_submodule(enrollment, 2)
    print(f"Progress: {enrollment.get_progress_percent():.0f}%")

    # 6. Student takes quiz (fails first)
    print("\n--- 6. Student Takes Quiz (Fails) ---")
    wrong_answers = {1: 1, 2: 0, 3: 0}  # All wrong
    platform.submit_quiz(enrollment, quiz, wrong_answers)

    # 7. Student retakes quiz (passes)
    print("\n--- 7. Student Retakes Quiz (Passes) ---")
    correct_answers = {1: 0, 2: 2, 3: 2}  # All correct
    platform.submit_quiz(enrollment, quiz, correct_answers)

    # 8. Complete last submodule
    print("\n--- 8. Complete Final Submodule ---")
    platform.complete_submodule(enrollment, 3)

    # Final status
    print("\n--- Final Status ---")
    print(f"Enrollment: {enrollment}")
    print(f"Course Complete: {enrollment.is_course_complete()}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)

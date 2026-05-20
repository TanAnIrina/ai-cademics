"""Acest script nu se rulează în timpul cursului normal 
(ca să nu adaugi overhead și timp de așteptare pentru elevi). El se rulează de către tine 
(QA Tester-ul) când faci o modificare la promptul profesorului (în build_teacher_prompt), 
pentru a te asigura că nu i-ai stricat logica și că produce în continuare teste de calitate 
bazate pe materia curentă. Dacă acest script dă PASS, înseamnă că poți face Push la codul
tău pe GitHub cu încredere."""


# run_evals.py
from eval_grading import eval_grade_reasoning_correlation
from eval_emotions import eval_emotional_accuracy

def main():
    print("=== EXECUTARE AUTOMATED EVALS ===")
    
    # Testare Eval 1 (Caz cu eroare logică intenționată - FAIL)
    eval_grade_reasoning_correlation(
        grade=9, 
        reasoning="The answer is completely wrong and shows no understanding of the subject."
    )

    # Testare Eval 1 (Caz corect - PASS)
    eval_grade_reasoning_correlation(
        grade=2, 
        reasoning="You failed to mention the core concepts and the sentences make no sense."
    )

    # Testare Eval 2 (Caz corect - PASS)
    eval_emotional_accuracy(
        frustration_level=9, 
        student_text="I don't even care anymore, this whole lesson is a waste of my time. Leave me alone."
    )

    # Testare Eval 2 (Caz cu eroare emoțională intenționată - FAIL)
    eval_emotional_accuracy(
        frustration_level=8, 
        student_text="Oh wow, I find this topic absolutely fascinating! I can't wait to learn more from our wonderful teacher."
    )

    
    #EVAL JUOURNALS
    # TEST CAZ 1: Un jurnal bun (PASS)
    good_journal = "I felt pretty annoyed during the History lesson today. The teacher gave me a low grade even though I thought my answer was okay. But I guess learning about the Roman Empire was kind of interesting. I'll try to study more so I don't get frustrated next time."
    eval_journal_reflection(
        student_name="Llama", 
        subject="The Roman Empire", 
        journal_text=good_journal
    )
    
    # TEST CAZ 2: Un jurnal prost (Nu e la persoana I, și e doar o descriere a materiei) (FAIL)
    bad_journal = "The Roman Empire was a large empire in history. It had many emperors. Rome was the capital. The military was very strong and conquered many lands."
    eval_journal_reflection(
        student_name="Qwen", 
        subject="The Roman Empire", 
        journal_text=bad_journal
    )

if __name__ == "__main__":
    main()
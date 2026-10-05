from backend.workflow import analysis_from_context, context_from_problem, question_from_context


def test_context_separates_known_unknowns_and_constraints():
    context = context_from_problem("I am a fresher with a very high workload and little energy to prepare for a job switch. I need stable income.")
    assert context["goal"]
    assert context["facts"]
    assert context["constraints"]
    assert context["unknowns"]
    assert context["assumptions"]


def test_analysis_has_human_decision_boundary():
    context = context_from_problem("My workload is too high and I want to switch jobs.")
    question = question_from_context(context, "My workload is too high and I want to switch jobs.")
    analysis = analysis_from_context(context, "My workload is too high and I want to switch jobs.", question["options"][0])
    assert analysis["reframe"]["possible"]
    assert analysis["synthesis"]["next_step"]
    assert all(option["reversibility"] for option in analysis["options"])

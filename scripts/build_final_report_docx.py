"""Build the final project report DOCX without external docx dependencies.

The project venv used in this workspace does not include python-docx, so this
script edits the OOXML package directly using only the Python standard library.
It uses the user's Report.docx as a package template and replaces word/document.xml.
"""
from __future__ import annotations

import html
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "Report.docx"
OUT = ROOT / "Report_final.docx"


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def run(text: str, *, bold: bool = False, italic: bool = False, size: int | None = None,
        color: str | None = None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if size:
        props.append(f'<w:sz w:val="{size * 2}"/>')
        props.append(f'<w:szCs w:val="{size * 2}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    return f"<w:r>{rpr}<w:t{preserve}>{esc(text)}</w:t></w:r>"


def para(text: str = "", *, style: str | None = None, align: str | None = None,
         before: int = 0, after: int = 120, line: int = 264,
         bold: bool = False, italic: bool = False, size: int | None = None,
         color: str | None = None, keep_next: bool = False) -> str:
    ppr = [f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>']
    if style:
        ppr.insert(0, f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    return f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{run(text, bold=bold, italic=italic, size=size, color=color)}</w:p>"


def heading(text: str, level: int) -> str:
    if level == 1:
        return para(text, style="Heading1", before=320, after=140, line=280,
                    bold=True, size=16, color="2E74B5", keep_next=True)
    if level == 2:
        return para(text, style="Heading2", before=240, after=100, line=280,
                    bold=True, size=13, color="2E74B5", keep_next=True)
    return para(text, style="Heading3", before=160, after=80, line=264,
                bold=True, size=12, color="1F4D78", keep_next=True)


def caption(text: str) -> str:
    return para(text, before=120, after=80, line=240, italic=True, size=10, color="555555")


def cell(text: str, width: int, *, header: bool = False) -> str:
    fill = '<w:shd w:fill="F2F4F7"/>' if header else ""
    tcpr = (
        f"<w:tcPr><w:tcW w:w=\"{width}\" w:type=\"dxa\"/>"
        f"{fill}<w:vAlign w:val=\"center\"/>"
        "<w:tcMar><w:top w:w=\"80\" w:type=\"dxa\"/><w:bottom w:w=\"80\" w:type=\"dxa\"/>"
        "<w:start w:w=\"120\" w:type=\"dxa\"/><w:end w:w=\"120\" w:type=\"dxa\"/></w:tcMar></w:tcPr>"
    )
    p = para(text, after=0, line=240, bold=header, size=9 if header else 9)
    return f"<w:tc>{tcpr}{p}</w:tc>"


def table(rows: list[list[str]], widths: list[int]) -> str:
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = (
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:left w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:right w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="D9D9D9"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="D9D9D9"/></w:tblBorders>'
    )
    tbl = [
        "<w:tbl><w:tblPr><w:tblW w:w=\"9360\" w:type=\"dxa\"/>"
        "<w:tblInd w:w=\"120\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/>"
        f"{borders}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>"
    ]
    for i, row in enumerate(rows):
        if i == 0:
            tbl.append("<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>")
        else:
            tbl.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>")
        for value, width in zip(row, widths):
            tbl.append(cell(value, width, header=i == 0))
        tbl.append("</w:tr>")
    tbl.append("</w:tbl>")
    return "".join(tbl)


def document_xml(body_parts: list[str]) -> str:
    sect_pr = (
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="708" w:footer="708" w:gutter="0"/>'
        '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}"><w:body>'
        + "".join(body_parts)
        + sect_pr
        + "</w:body></w:document>"
    )


def build_parts() -> list[str]:
    parts: list[str] = []
    parts.append(para("Guidance-Level Policy Verification in Dual-Control Tool Agents",
                      align="center", after=80, line=280, bold=True, size=18, color="0B2545"))
    parts.append(para("Yue Cao", align="center", after=180, line=260, size=11, color="555555"))

    parts.append(heading("Abstract", 1))
    parts.append(para(
        "AI assistants increasingly work by advising another actor rather than directly changing the world. A support assistant "
        "may tell a user how to change a phone setting, an office automation agent may tell a human operator which record to update, "
        "and a workflow agent may coordinate with another specialized agent that performs the final action. These settings expose a "
        "gap in standard tool-agent verification: checking the assistant's own tool calls does not check whether its instructions "
        "lead someone else toward a wrong action. This project studies whether a verifier placed on the guidance channel can close "
        "that gap. I test a sequence of increasingly refined designs: a policy-based verification-repair module, a self-revision "
        "variant, and a narrower prerequisite-based checker. The experiments provide attribution and ablation evidence that user-side "
        "guidance is a recurring bottleneck in this benchmark slice, but they do not show that the tested final-message interventions "
        "reliably improve task completion. The main lesson is architectural: when policy rules depend on hidden environment conditions "
        "and multi-step diagnosis, verification should move upstream from rewriting the "
        "last natural-language instruction to checking a structured plan and its supporting evidence."
    ))

    parts.append(heading("1. Introduction", 1))
    parts.append(para(
        "Many useful AI systems are not single actors that directly execute every consequential action. In everyday technical-support "
        "and operations workflows, an assistant often observes the situation, reasons about the next step, and then instructs a human "
        "or another agent to perform the final action. The instruction itself becomes part of the control loop: if it is premature, "
        "ambiguous, or based on the wrong diagnosis, the downstream actor can change the environment incorrectly even though the "
        "assistant's own tool calls look safe."
    ))
    parts.append(para(
        "Most tool-agent verification work fits a single-control view of agency. The base agent proposes a structured tool call, "
        "the verifier checks the proposed action against a policy or precondition, and an unsafe action can be blocked before "
        "execution. This structure is powerful because the action is explicit and machine-readable. It becomes weaker when the "
        "critical action is only implied by natural-language guidance to someone else."
    ))
    parts.append(para(
        "This report studies a dual-control version of verification: the assistant and the user both affect the environment, but "
        "through different action channels. The motivating question is simple: if the assistant can fail by giving bad guidance, "
        "can an online verifier check and repair that guidance before the user acts? In the tested implementations, the answer is "
        "negative: final-message repair does not produce a reliable pass@1 gain. This does not prove that guidance verification is "
        "impossible; it suggests that the final instruction is often too late and too unstructured as the main object of verification."
    ))
    parts.append(para(
        "The report follows the same progression as the project. I first build a direct verification-repair architecture over the "
        "assistant's last user-facing message. I then use oracle and hard-task ablations to ask whether failures are caused by "
        "bad wording, bad guidance, or upstream diagnosis and planning. Finally, I revise the verifier's role from policy violation "
        "classification to prerequisite checking, and find that this better-scoped final-message verifier still does not solve the "
        "core problem. The resulting main claim is not that guidance verification is useless, but that it must target the agent's "
        "planned user action and evidence before the final sentence is written."
    ))

    parts.append(heading("2. Project Logic and Method", 1))
    parts.append(heading("2.1 Progressive Research Questions", 2))
    parts.append(para(
        "The project is organized as a sequence of diagnostic questions rather than a single method claim. The first question is "
        "whether guidance failures are common enough to matter. The second is whether a direct verification-repair module over the "
        "final message improves success. The third is whether failures remain after planning is made easier with oracle information. "
        "The fourth is whether a better-scoped verifier, focused on explicit diagnostic evidence, fixes the main weakness of the "
        "original verifier."
    ))
    parts.append(caption("Table 1. Progressive logic of the project. Each stage answers a narrower question revealed by the previous stage."))
    parts.append(table([
        ["Stage", "Question", "Design used", "What a positive result would suggest"],
        ["1. Identify the channel", "Do failures concentrate on the user-controlled side?", "Baseline runs with failure-location analysis", "User-side failed checks are common enough to investigate."],
        ["2. Direct intervention", "Can final-message verification-repair improve success?", "Policy-rubric verifier plus external repair", "Local message repair may be enough to recover some failures."],
        ["3. Bottleneck decomposition", "Is the problem really guidance, or earlier planning?", "Oracle-plan and oracle-plan/no-user ablations", "If oracle plans help, diagnosis/planning is a major bottleneck."],
        ["4. Revision control", "Does feedback to the base agent help more than external rewriting?", "Self-revise and placebo-revise", "Policy feedback matters beyond resampling."],
        ["5. Role redesign", "Is prerequisite checking a better verifier responsibility?", "Deterministic precondition checker", "The verifier should check evidence before action."],
    ], [1100, 2500, 2700, 3060]))

    parts.append(heading("2.2 Verification-Repair Architecture", 2))
    parts.append(para(
        "The initial architecture mirrors the standard verifier-controller loop, but moves the intervention point from tool calls "
        "to user-facing guidance. The base agent first generates a normal response. A hook intercepts the response only if it is "
        "natural-language guidance to the user rather than a tool call. The verifier then checks this candidate message against a "
        "policy-derived rubric. If the verifier accepts the message, it is delivered unchanged; if it rejects the message, the system "
        "either rewrites the instruction externally or asks the base agent to regenerate it with policy feedback."
    ))
    parts.append(para(
        "This design is intentionally local. It does not retrain the base agent, change the user simulator, or alter provider-side "
        "tool calls. That makes the ablation clean: differences between methods come from what happens to the guidance message. The "
        "same locality also becomes the design's main weakness. When a policy rule depends on hidden state or on a diagnostic result "
        "from several turns earlier, the verifier must infer whether the rule applies from a long natural-language transcript. This "
        "is why the repair module often changes correct or harmless instructions: it is checking a sentence when the real object of "
        "verification should be the agent's decision process."
    ))
    parts.append(heading("2.3 Revised Precondition Checker", 2))
    parts.append(para(
        "The final method variant changes the verifier's responsibility from policy violation classification to action precondition checking. "
        "It asks whether the assistant has explicitly established enough evidence to justify asking the user to perform a state-changing "
        "action. For example, before asking the user to reset a device setting, the transcript should contain a relevant diagnostic "
        "read. If that evidence is absent, the system replaces the instruction with a request for the diagnostic. This checker is "
        "deterministic and has no verifier-token cost, but it is still applied at the final-message layer."
    ))

    parts.append(heading("3. Experimental Conditions", 1))
    parts.append(para(
        "The experiments use a telecom-support benchmark because the domain naturally separates provider-side actions from user-side "
        "device actions. The assistant can query or update provider records, while the user performs actions such as checking device "
        "state, changing network settings, granting permissions, or rebooting. The base model is GPT-4.1-mini, and the verifier/repair "
        "model is GPT-4o-mini when an LLM verifier is used."
    ))
    parts.append(para(
        "The main metrics are pass@1, pass^2, error rate, verifier token cost, and failure attribution. A failed completed run is "
        "counted as user-side when the failed expected action or final environment assertion is on the user side. Crashes and max-step "
        "timeouts are counted as incomplete errors rather than forced into either guidance or agent-action failure. This attribution "
        "identifies where the unresolved requirement appears in the trajectory; it is not, by itself, proof that one specific sentence "
        "caused the failure."
    ))
    parts.append(heading("3.1 Task Sets and Difficulty Labels", 2))
    parts.append(para(
        "The reported experiments use four data slices. The table below lists only the task sets used for evaluation; analyses such "
        "as repair-oracle selection, gated repair, self-revision, placebo revision, and precondition checking are experimental "
        "conditions reported in the results tables, not separate datasets. In all tables, baseline denotes the unmodified dual-control "
        "agent with no guidance verifier."
    ))
    parts.append(caption("Table 2. Task sets used by the reported experiments."))
    parts.append(table([
        ["Task set", "Source", "Scale", "Composition and difficulty"],
        ["Single-fault Telecom set", "telecom_small", "20 tasks", "Low-difficulty slice with one injected fault per task; 6 MMS, 8 mobile-data, and 6 service tasks."],
        ["Full-domain 60-task sample", "telecom_full seed-0 sample", "60 tasks", "Broader multi-fault sample: mean 4.78 faults per task, range 1-8; 48 MMS, 9 mobile-data, and 3 service tasks."],
        ["Hard 12-task diagnostic set", "hard_task_ids.json", "12 tasks", "Handpicked difficult Telecom slice: mean 4.83 faults per task, range 2-9; 7 MMS, 4 mobile-data, and 1 service task."],
        ["Hard 4-task stress set", "trace_task_ids.json", "4 tasks", "Balanced pressure test: mean 6.50 faults per task, range 5-9; 3 MMS and 1 mobile-data task. The same four tasks are used for gated repair, self-revision, placebo, and precondition-checker follow-ups."],
    ], [2100, 2200, 1200, 3860]))

    parts.append(caption("Table 3. Experimental condition architecture. The table spells out what each condition changes and what question it answers."))
    parts.append(table([
        ["Condition", "Agent/planning setup", "Verifier or intervention", "Purpose"],
        ["baseline", "Base dual-control agent plans and guides by itself.", "No verifier.", "Measures the original task difficulty and failure attribution."],
        ["detect-only verifier", "Same as baseline.", "LLM verifier checks the final guidance but does not change it.", "Separates detection cost/noise from repair effects."],
        ["verifier + repair", "Same as baseline.", "LLM verifier rewrites rejected user-facing guidance once.", "Tests the original verification-repair idea."],
        ["oracle repair", "Paired baseline and repair-all trajectories.", "A perfect selector chooses the better outcome after the fact.", "Estimates the maximum headroom of final-message repair."],
        ["gt", "Agent receives ground-truth resolution steps but must still guide the user.", "No verifier.", "Tests whether planning/diagnosis is the bottleneck."],
        ["gtsolo", "Agent receives ground-truth steps and can execute all tools itself.", "No user-guidance channel.", "Upper bound when both planning and user communication are removed."],
        ["oracle plan + gated repair", "Oracle-plan agent still guides the user.", "Verifier-repair fires only on mutating user instructions.", "Tests whether repair helps after planning is mostly solved."],
        ["selfrevise", "Base agent plans by itself.", "Verifier critique is injected back so the base agent regenerates.", "Tests whether policy feedback helps more than external rewriting."],
        ["placebo", "Same trigger as selfrevise.", "Content-free rephrase feedback.", "Controls for the effect of resampling alone."],
        ["precondition checker", "Base agent plans by itself.", "Deterministic prerequisite checker replaces unsupported actions with diagnostic requests.", "Tests a narrower verifier role without LLM policy classification."],
        ["gt + precondition checker", "Oracle-plan agent guides the user.", "Same deterministic prerequisite checker.", "Tests whether prerequisite checking helps when planning is given."],
    ], [1400, 2500, 3000, 2460]))

    parts.append(heading("4. Experimental Results", 1))
    parts.append(para(
        "The first research question is whether failures concentrate on the user-controlled side of the dual-control environment. "
        "The baseline failure-location results answer this before any repair method is considered. On the single-fault Telecom set, "
        "baseline has 15 completed failures after excluding 2 incomplete errors; 14 of those 15 completed failures involve user-side "
        "failed checks, giving a 0.933 user-side failure share among completed failures. On the hard 4-task stress set, baseline has "
        "14 completed failures after excluding 2 incomplete errors, and all 14 involve user-side failed checks. The unbalanced hard "
        "12-task diagnostic baseline shows the same pattern with a 1.000 user-side failure share, but is used only as diagnostic "
        "support. These counts locate the unresolved requirements on the user side; they do not prove that a specific assistant "
        "instruction caused the failure."
    ))
    parts.append(caption("Table 4. Single-fault and oracle-repair results. Higher pass@1 is better; lower error rate and token cost are better."))
    parts.append(table([
        ["Experiment", "Condition", "Tasks/trials", "pass@1", "error/headroom", "Key interpretation"],
        ["Single-fault Telecom set", "baseline", "80 trials", "0.787", "error 0.025", "Strong baseline; many completed failures are user-side by attribution."],
        ["Single-fault Telecom set", "verifier + repair", "80 trials", "0.775", "error 0.050; 1.26M verifier tokens", "No observed improvement over baseline and substantially higher cost."],
        ["Single-fault repair oracle", "baseline / repair-all / oracle", "20 paired tasks", "0.900 / 0.800 / 0.900", "headroom +0.000", "No measurable repair headroom on single-fault tasks."],
        ["Full-domain 60-task repair oracle", "baseline / repair-all / oracle", "60 paired tasks", "0.250 / 0.200 / 0.300", "headroom +0.050", "Repair converts 3 failures but breaks 6 successes."],
    ], [1800, 1800, 1300, 1000, 1800, 1660]))

    parts.append(heading("4.1 Final-message repair does not improve task completion", 2))
    parts.append(para(
        "The single-fault experiment does not support external guidance repair as an effective intervention in this implementation. "
        "Baseline reaches 0.787 pass@1, while verifier + repair reaches 0.775 with a higher error rate and 1.26M verifier "
        "tokens. Because the detect-only condition also differs from baseline, this single-fault comparison contains sampling noise; "
        "however, it is enough to reject a strong claim that final-message repair clearly improves task success."
    ))
    parts.append(para(
        "The oracle repair experiments provide stronger evidence. On the single-fault set, a perfect selector over baseline and repair-all "
        "has zero headroom. On the 60-task full-domain sample, the oracle selector improves pass@1 by only +0.050. More importantly, "
        "repair-all fixes 3 baseline failures but breaks 6 baseline successes. This asymmetry is the central empirical finding: "
        "sentence-level repair has limited upside and a concrete risk of damaging correct trajectories."
    ))

    parts.append(heading("4.2 Planning and diagnosis dominate the hard tasks", 2))
    parts.append(caption("Table 5. Hard-set ablations and follow-up results. Some hard 12-task rows are diagnostic because trial counts differ or files are dirty; all hard 4-task rows are balanced 4 tasks x 4 trials."))
    parts.append(table([
        ["Setting", "Condition", "pass@1", "error rate", "Interpretation"],
        ["Hard 12-task diagnostic set", "baseline", "0.341", "0.000", "Unbalanced file; diagnostic only. Base agent struggles on hard tasks."],
        ["Hard 12-task diagnostic set", "oracle plan (gt)", "0.708", "0.000", "Ground-truth steps substantially improve success."],
        ["Hard 12-task diagnostic set", "oracle plan + no user (gtsolo)", "1.000", "0.000", "With plan and no guidance channel, the tasks are solvable."],
        ["Hard 4-task stress set", "baseline", "0.000", "0.125", "The selected multi-fault tasks are too hard for the base agent."],
        ["Hard 4-task stress set", "oracle plan (gt)", "0.562", "0.062", "Planning/diagnosis explains much of the failure."],
        ["Hard 4-task stress set", "gt + gated final repair", "0.438", "0.000", "Repair does not beat oracle-plan baseline."],
        ["Hard 4-task stress set", "self-revise", "0.062", "0.500", "Revision loop is unstable; use as implementation diagnosis only."],
        ["Hard 4-task stress set", "placebo revise", "0.125", "0.438", "Resampling control is similarly unstable."],
        ["Hard 4-task stress set", "precondition checker", "0.062", "0.312", "One success but high incompletion; no reliable gain over baseline."],
        ["Hard 4-task stress set", "gt + precondition checker", "0.438", "0.062", "Still below gt, so prerequisite replacement alone is not enough."],
    ], [1700, 2200, 1000, 1000, 3460]))
    parts.append(para(
        "The hard-task decomposition helps explain why final-message repair may have little leverage. In the hard 4-task stress set, "
        "baseline completes no trials, but oracle-plan prompting reaches 0.562 pass@1. This indicates that the base model often "
        "fails before the final instruction is written: it has not correctly diagnosed the fault combination or chosen the right "
        "sequence of user and assistant actions."
    ))
    parts.append(para(
        "The comparison between gt and gt plus gated repair is the cleanest test of the original intervention. If final guidance "
        "repair were the missing capability after planning is solved, it should improve over the oracle-plan baseline. Instead, "
        "it drops from 0.562 to 0.438 on the hard 4-task stress set. The repaired system is cleaner in terms of runtime errors, but it does "
        "not convert that into task success."
    ))

    parts.append(heading("4.3 Precondition checking is better scoped but still too local", 2))
    parts.append(para(
        "The last two rows of Table 5 report the precondition-checker follow-up on the same hard 4-task stress set. This checker does not use an LLM to judge "
        "policy violations. It deterministically recognizes state-changing user actions and verifies whether the transcript already "
        "contains the corresponding diagnostic evidence. If not, it replaces the instruction with a diagnostic request. This design "
        "avoids verifier-token cost and removes the earlier LLM rule-matching false positives."
    ))
    parts.append(para(
        "The follow-up does not provide positive evidence for final-message prerequisite replacement. In the self-planning setting, the precondition checker reaches only "
        "0.062 pass@1 with a 0.312 error rate. Under the stronger oracle-plan condition, gt + precondition checker reaches 0.438 pass@1, below the "
        "0.562 gt baseline. Trace inspection shows that the checker often turns necessary actions into additional diagnostic requests, "
        "especially for network mode, airplane mode, reboot, permissions, and APN. This reduces one source of semantic false positives "
        "but still interrupts the troubleshooting trajectory at the final-message layer."
    ))

    parts.append(heading("4.4 Self-revision is inconclusive because the implementation is unstable", 2))
    parts.append(para(
        "The self-revise and placebo rows in Table 5 are the experimental evidence for this branch. Self-revise reaches only 0.062 "
        "pass@1 with a 0.500 error rate, while placebo revise reaches 0.125 pass@1 with a 0.438 error rate. These rows should not be "
        "interpreted as a substantive failure of self-repair in general because the error rate comes mainly from MAX_STEPS timeouts, "
        "not API crashes. Trace analysis shows two causes. First, the procedural verifier "
        "over-triggers on semantically related but incorrect rules, such as treating airplane-mode or SIM instructions as roaming "
        "violations. Second, the regeneration mechanism appends the rejected draft and the reflection into the agent's hidden state, "
        "so the agent later reasons over messages the user never saw. These artifacts make the current self-revision result an "
        "implementation limitation rather than a reliable method comparison."
    ))

    parts.append(heading("5. Why Verification-Repair Misrepairs", 1))
    parts.append(para(
        "The original verification-repair architecture fails for structural reasons, not just because one prompt was imperfect. "
        "It asks a verifier to judge a final sentence, but the correctness of that sentence often depends on hidden environment "
        "state and earlier trajectory decisions. If the assistant says to change a setting, whether that is good advice depends on "
        "what has already been diagnosed, what the current state is, and whether the action fits the intended troubleshooting plan."
    ))
    parts.append(para(
        "The first failure mode is observability. The verifier does not have direct environment tools; it only sees the message and "
        "a transcript. Many policy clauses are conditional on facts such as whether a setting is already enabled, whether a permission "
        "is missing, or whether a diagnostic result justifies a repair. Without direct state access or a structured state summary, the "
        "verifier must infer these facts from text. This creates false positives, especially when the transcript is long or when the "
        "policy contains similar words for different actions."
    ))
    parts.append(para(
        "The second failure mode is timing. A final-message verifier can only edit what the agent is about to say; it cannot easily "
        "repair the reason the agent chose that step. If the diagnosis is wrong, or if the agent has lost track of which faults have "
        "already been resolved, replacing the sentence with a safer diagnostic request may only lengthen the conversation. This is why "
        "the deterministic precondition checker is better specified but still underperforms: it reduces semantic guessing, yet remains "
        "too reactive."
    ))
    parts.append(para(
        "The third failure mode is representation. Natural-language guidance is a lossy object for verification. It mixes intent, "
        "rationale, user-facing politeness, and sometimes several possible actions in one paragraph. A verifier should instead inspect "
        "a structured next-step plan: the proposed user action, the evidence supporting it, the required preconditions, and the expected "
        "effect. Only after that plan is accepted should the assistant turn it into user-facing language."
    ))

    parts.append(heading("6. Limitations", 1))
    parts.append(para(
        "The benchmark is useful but limited. It provides a controlled dual-control environment with explicit user-side and assistant-side "
        "actions, but it is still a simulator. The user simulator may react differently from real users, and the task set emphasizes a "
        "particular support domain with scripted tools and deterministic evaluation criteria. The hard 4-task stress set is intentionally "
        "stressful and small, so it is best used for diagnostic analysis rather than broad performance claims."
    ))
    parts.append(para(
        "The method is also limited by design. The main verifier sees only messages and transcripts, not direct environment state. The "
        "self-revision implementation is unstable because regeneration can pollute the agent's hidden state and produce max-step loops. "
        "The deterministic precondition checker avoids LLM verifier cost, but it still edits the final message instead of supervising the "
        "agent's plan. Finally, the base model is a lightweight non-reasoning model, so some failures reflect planning capacity rather "
        "than only the verification mechanism."
    ))
    parts.append(para(
        "These limitations do not invalidate the main empirical pattern, but they bound it. The report should not claim that guidance verification "
        "cannot work in general. The supported claim is narrower: in this benchmark slice, final-message verification-repair and final-message "
        "prerequisite replacement do not reliably improve success, and the evidence motivates plan-level verification as a more plausible "
        "intervention point."
    ))

    parts.append(heading("7. Conclusion", 1))
    parts.append(para(
        "This project began with the hypothesis that guidance-level verification could improve dual-control tool-agent performance. "
        "The evidence supports a narrower claim. User-side failures are common in tau2 Telecom, but final-message "
        "policy repair does not improve pass@1 and has low oracle headroom. A deterministic precondition checker is better "
        "aligned with the conditional structure of the Telecom policy, but it also fails to beat the oracle-plan baseline when applied "
        "as final-message replacement. The most meaningful contribution is therefore diagnostic: the experiments identify why a naive "
        "transfer of single-control action verification can fail in this dual-control setting and motivate structured user-action plan "
        "verification as the next design."
    ))

    parts.append(heading("Claim-Evidence Map", 1))
    parts.append(table([
        ["Claim", "Evidence used in this report", "Status"],
        ["User-side failed checks are a recurring failure location.", "Single-fault baseline: 14/15 completed failures involve user-side failed checks; hard stress baseline: 14/14 completed failures involve user-side failed checks.", "Supported as failure-location/bottleneck evidence, not as sentence-level guidance-causality proof."],
        ["Final-message repair does not improve task success.", "Single-fault repair 0.775 vs baseline 0.787; hard stress gt+repair 0.438 vs gt 0.562.", "Supported for this implementation and benchmark slice."],
        ["Repair headroom is small.", "Oracle full60 improves only from 0.250 to 0.300 and breaks 6 successes while converting 3 failures.", "Supported."],
        ["Planning/diagnosis is a major bottleneck.", "Hard stress baseline 0.000 vs gt 0.562; hard diagnostic gt 0.708 vs baseline diagnostic 0.341.", "Supported."],
        ["Precondition checking is not sufficient at the final-message layer.", "Precondition checker 0.062; gt + precondition checker 0.438 vs gt 0.562 on the hard stress set.", "Supported for the deterministic prerequisite-repair implementation."],
        ["Self-revision is unresolved.", "Self-revise error rate 0.500 and placebo error rate 0.438 on the hard stress set; MAX_STEPS trace failures.", "Needs cleaner implementation before method claims."],
    ], [2600, 4800, 1960]))

    return parts


def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else OUT
    tmp = OUT.with_suffix(".tmp.docx")
    shutil.copyfile(TEMPLATE, tmp)
    xml = document_xml(build_parts())
    with zipfile.ZipFile(tmp, "r") as zin:
        entries = {item.filename: zin.read(item.filename) for item in zin.infolist()}
    entries["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)
    tmp.unlink(missing_ok=True)
    print(out)


if __name__ == "__main__":
    main()

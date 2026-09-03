# Part 3 - Prompt Engineering Comparison

***Analytical Question Chosen:*** How should a BI analyst communicate data limitations to a non-technical audience?

## Strategy 1 - Zero-Shot
**Prompt sent:** How should a BI analyst communicate data limitations to a non-technical audience?

**Response:** Communicating data limitations well is really about translating technical caveats into plain-language implications the audience can actually use when making decisions — without either hiding the caveats or burying people in jargon that makes them tune out.

A few principles that tend to work well:

Lead with what it means for the decision, not the technical mechanism. Instead of "the sample has a 12% response rate and potential nonresponse bias," say something like "these results likely skew toward our most engaged customers, so the real picture across all customers could look somewhat different." The audience needs to know how much weight to put on the finding, not the statistical vocabulary behind it.

Use concrete analogies and visuals instead of statistical terms. A margin of error becomes "this number could reasonably be anywhere between X and Y." A confidence interval becomes a shaded range on a chart rather than a percentage...

**Evaluation - What did this strategy do well? What was missing or generic?** The strategy did well by directly answering the question and staying focused on the main point. The response was clear, easy to understand, and provided specific strategies for communicating data limitations without using unnecessary technical jargon. However, the response was somewhat generic because it was not tailored to a specific audience, business situation, or dataset. It also did not provide as much practical guidance for how a BI analyst could communicate these limitations in an actual business presentation or dashboard.

## Strategy 2 - Role-assigned
**Prompt sent:** You are a senior BI analyst presenting findings to a non-technical audience of business executives. How should you communicate data limitations so that the audience understands how those limitations affect their decisions without becoming overwhelmed by technical details?

**Response:** This is a conversational question, not a task requiring files or research, so I'll just answer directly.

The core discipline is separating "what this means for your decision" from "why the data is imperfect." Executives need the first; they'll tune out if you lead with the second.

A few practical habits:

Lead with the decision impact, not the caveat. Instead of "this survey has a 12% response rate and potential self-selection bias," say "we're fairly confident about the direction of this trend, less confident about the exact size — I'd treat the 15% figure as 'somewhere between 10-20%' rather than a precise number." Executives can act on a range; they can't act on a methodology lecture.

Use a confidence label, not a confidence lecture. A simple "high confidence / directional / early signal" tag next to each finding does more work than a paragraph of methodology. If you want one...

**Evaluation - What did this strategy do well? What was missing or generic?** This strategy did well by making the response more tailored to a specific professional role and audience. Assigning Claude the role of a senior BI analyst and identifying business executives as the audience encouraged it to focus on decision-making and practical business implications rather than technical details. Compared with the zero-shot response, the advice felt more actionable for a BI analyst working with executives. However, some of the recommendations were still somewhat generic because they were not applied to a specific business situation, dataset, or dashboard.

## Strategy 3 - Few-shot
**Prompt sent:** I want you to answer the following question using the few-shot prompting strategy.

First, I’ll provide an example of the format and structure I want you to follow. The example is only meant to demonstrate the output format—it does not answer the question.

Example output format:

Main Point: State the key takeaway clearly and simply.
Why It Matters: Explain why this is important for the audience.
Practical Example: Give an example of how this could be communicated in a real-world situation.

Now answer this question using that same structure:
How should a BI analyst communicate data limitations to a non-technical audience?

**Response:** 

Main Point: A BI analyst should tell the audience what the data can and can't support before presenting conclusions, using plain language instead of technical caveats like "sample size" or "confidence interval."

Why It Matters: Non-technical stakeholders often treat any number in a dashboard or slide as fact. If an analyst doesn't flag gaps — missing data, a small sample, a reporting lag, or a metric that doesn't capture the full picture — decision-makers may act on a number with more certainty than it deserves, leading to poor decisions and a loss of trust once the limitation surfaces later.

Practical Example: Instead of saying "n=42, so results may not be statistically significant," the analyst could say: "We only have data from 42 customers so far, so this trend is worth watching, but I wouldn't make a major decision until we have more data." Or: "This chart doesn't include walk-in sales yet,

**Evaluation - What did this strategy do well? What was missing or generic?** The few-shot strategy did well because it gave Claude a clear example of the structure and level of detail expected before asking the actual question. This resulted in an organized response with distinct sections for the main point, why it matters, and a practical example. The response was easy to understand and gave concrete examples of how a BI analyst could communicate data limitations. However, the examples were still somewhat generic because they could apply to many BI situations without addressing a particular industry, dataset, or business decision. The prompt also focused more on formatting than on providing specific business context.

### Conclusion

Overall, each prompting strategy improved the response in a different way. The zero-shot strategy provided a clear and useful general answer, but it was the most generic because it had no additional guidance. The role-assigned strategy produced a more practical response by focusing on the needs of business executives and connecting data limitations to decision-making. The few-shot strategy produced the most organized output because the example gave Claude a specific structure to follow, making it the most useful for a BI analyst who needs to communicate information clearly and consistently.

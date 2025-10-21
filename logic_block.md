# Logic Block

**Goal**  
- [What the block/system should achieve (success condition).]
- Extract Fed SOMA holdings data from their official endpoint, clean up the data, and use it to draw conclusions about market movement

**Inputs**  
- [What comes in: type(s), assumptions.]
- Fed SOMA data in CSV form(use the summary data, not detailed)
- 

**Outputs**  
- [Explicit form of result: type, format, conditions.]  
- Dashboard using plotly and matlib to create visuals using the data

**Constraints / Invariants**  
- [Rules that must always hold, e.g., type safety, performance, code constraints.]  
- The program should work as long as the endpoint for the Fed SOMA data doesn't change
- Automatically updates without having to regenerate the entire dataset, as the dataset is large
- When extracting dataset, must account for holidays as well as days where the market isn't open

**Rules (IF/THEN)**  
- [Decision logic in plain IF/THEN statements.]  
- 
**Flow**  
1. [Step 1]  
2. [Step 2]  
3. [Step 3]  

**Edge Cases**  
- [Case 1: Expected result]  
- [Case 2: Expected result]  
- [Case 3: Expected result]  

**Tests / Checks**  
- Input → Expected Output  
- Input → Expected Output  

**Variations**  
1. [Variation 1]  
2. [Variation 2]  

**Narration**  
> [Write a short paragraph as if explaining your reasoning to another person.
   What choices did you make? Why this approach vs. alternatives?]

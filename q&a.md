Good start — those are the kinds of questions a technical reviewer or hiring manager would ask. Here’s a structured expansion list grouped by **Data**, **Design**, **Implementation**, and **Purpose** — covering almost every angle someone could ask about your project.

---

### **Data Choices**

1. Why was `.csv` chosen over formats like `.json` or `.parquet` for the core data source?
    - CSV was one of the available forms of output from the fed endpoint. The other 2 options were XML and JSON. I chose CSV because it was a format I was learning at the time, and it seemed to make sense for the type of data, mostly numeric. Not as familiar with XML and JSON
2. Why summary data from the Fed’s SOMA endpoint instead of detailed or security-level data?
    - The point of this project is to create an overview of the long term movement of the Fed, and create conclusions such as 'the government is supporting the housing industry' or 'the government is pulling out of the housing industry'. Because detailed data would be hundreds of times larger than the summary as well as being mostly redundant and unneeded, summary data was deemed to be the correct data we needed
3. Why not pull directly from the Fed API each time instead of saving local CSVs?
    - Because the date range can be decades long, even just compiling the initial fill can take several minutes. Also, while this program does require internet connection to download from the endpoint as well as assemble the chart with Plotly CDN, after you download it you can use and view the data whenever
4. Why is data updated incrementally week by week instead of fetched all at once?
    - The Fed API limits requests to only 2 weeks of data. So it is impossible to fetch all of them at once. I tried workarounds but they didn't work. Choosing to download 1 week at once instead of 2 weeks seemed to be the neater solution.
5. Why was the “wide” format chosen for plotting while the “long” format is just for validation?
    - The wide format is cleaner for traditional chart creation. Not sure why long is here
6. Why produce both CSV and Parquet outputs if only one is used downstream?
    - CSV is the baseline format; simple, readable, and widely supported. Parquet was added because it is faster to read for large datasets and later analytics. Even if the current pipeline doesn't use it, exporting a Parquet version future-proofs the repo and data for future work.(analytical workloads, storage efficiency, schema preservation)
7. How do you ensure historical consistency if the Fed revises past weeks’ data?
    - Currently there are no guards in place for that, once the data is downloaded, there are guards against duplicate data, and if there are duplicate data it will keep the oldest one. To ensure historical consistency, the user has to purge the old data and backfill from scratch.
8. What are the trade-offs between storing raw vs. summarized (aggregated) data?
    - The raw data is much larger, and requires more cleaning and schema management
    - Summarized data is used directly by the dashboard and is the only data we need for this specific pipeline

---

### **Processing / Library Choices**

9. Why use **Pandas** for cleaning and aggregation instead of standard Python CSV operations or SQL?
    - Pandas was used for its DataFrame object and methods, which is very similar to a table. While python has some functions for that, pandas is just more efficient. 
    - SQL would require a database engine setup. pandas is faster to iterate locally for small to medium datasets
10. Why not use **NumPy** directly since the data is numeric?
    - NumPy alone is optimized for numeric arrays, but not labeled data. Pandas wraps NumPy to provide table-like operations, which fit this data's mixed column types and named structure
11. Why separate validation logic (`sanity_check.py`) from the dashboard code instead of embedding it?
    - The validation logic is separate because you might want to just check the data form is correct without creating the dashboard. It's just the benefits of modularity.
12. Why use `np.isclose` with tolerances instead of requiring exact matches between totals and sums?
    - Apparently in real world data there is often small mistakes caused by decimal points or other factors. Requiring exact matches could create a lot of errors with validation. Tolerance was added to reduce the noise
13. Why choose absolute + relative tolerances of `1e3` and `5e-3` specifically?
    - Given the size of the numbers, trillions of dollars, $1000 and 0.5% were deemed by AI to be appropriate
14. Why keep negative component values as warnings instead of forcing them to zero?
    - There are edge cases where the data can return negative values. In this case, it's better to create warnings to let the user self validate since it's not possible to validate in that case. Forcing them to zero could mutate or corrupt the data
15. Why not add unit tests or CI if this pipeline is meant to be reproducible?
    - This repo's goal was exploration and learning, not production deployment. At the prototype stage, correctness was visually verified through charts and manual snaity checks.
    - CI is planned later once the code becomes manually reproducible

---

### **Dashboard & Visualization Design**

16. Why use **Plotly** instead of Matplotlib, Seaborn, or Altair?
    - Plotly was chosen because it produces interactive, browser-renderable charts out of the box (zooming, panning, tooltips, toggling traces) with zero server setup. 
    - Matplotlib and Seaborn produce static plots meant for PDFs or notebooks.
    - Altair is declarative and nice for quick visualizations, but Plotly integrates better with Pandas and standalone HTML export.
    - Since this dashboard is about exploration and distribution without dependencies, Plotly gives the best “export to HTML and open anywhere” experience.
17. Why export as **HTML** instead of PNG or PDF?
    - HTML because the charts has buttons and draggable date ranges allowing user interaction. PNG doesn't allow that, and i'm not sure if PDF does
18. Why not build an interactive web app (e.g., Dash, Streamlit) instead of static HTML?
    - static html allows the data to be viewed without internet. for this project's scale, it's about making the pipeline and learning the skills for doing so, rather than sharing the results
19. Why specifically five charts — what does each one contribute to the overall interpretation?
    - The main story to get from the data is 'what is the Fed doing with its huge amount of cash?' and drawing conclusions from that. The most important charts are the week over week, cumulative change, and total holdings charts. Composition share and levels were added for fun, exploring more of plotly
20. Why place the cumulative chart second and total chart last — what’s the intended narrative flow?
    - Start with short-term movement (Weekly Change)
    - Then see how those movements accumulate (Cumulative Change)
    - Then break it down by composition (Levels and Shares)
    - Finally zoom out to total scale (Total Holdings) — the big picture.
21. Why include both composition levels and composition shares — don’t they overlap?
    - The two together separate “scale” from “mix.” One tells how big; the other tells what’s inside.
22. Why set `trillions=False` for dollar formatting?
    - If it was set to true it would lose some clarity. Some of the numbers would be shorted to 1.0T, which might undermine the scale of the charts. Many weekly data is in billions, truncating it to 0.0T hides precision. Setting trillions=False preserves readability across different scales
23. Why use rolling averages (in `fig_weekly_change`) — what insight does that add?
    - It calculates the rate of change, which can show whenever there are big moves being made. Usually it's pretty stable one way or another, but at times there are outliers to look out for. Weekly data can be noisy; a rolling mean smooths short-term fluctuations, highlighting sustained trends

---

### **Code Architecture**

24. Why structure everything as standalone scripts (`*.py`) instead of a package/module with imports?
    - Since the project is educational and the scope of the pipeline isn't too large, separating different parts of the pipeline into .py files was enough
25. Why use the `__main__` guard instead of building a CLI or Makefile entry point?
    - ? only just learning main guard right now
26. Why use constants (`ANCHOR_DATE`, `ZOOM_YEARS`) hard-coded rather than a config file or CLI args?
    - don't think there's a great excuse for this, but scope wasn't that large at the time
27. Why call helper functions like `add_ranges`, `dollars_axis_layout`, and `qt_annotation` instead of writing everything inline?
    - That's the point of writing helper functions. Because they are reused multiple times, defining them first allows you to call them modularly
28. Why rely on Plotly CDN for JS delivery — what’s the benefit or risk?
    - Plotly CDN allows the html file to be much more compact, but the downside is it requires internet connection at the time of running the dashboard script. 
29. Why use pure string concatenation to assemble HTML rather than a template engine (e.g., Jinja2)?
    - Probably again, for learning

---

### **Project Purpose / Broader Context**

30. What was the goal of this project — personal study, automation demo, or portfolio piece?
    - All three. This was made to be an automation demo proof of concept, but eventually be used as personal study, and once I owned every part of the repo, I would make it my portfolio piece, demonstrating ownership and technical range
31. What kind of user is this dashboard intended for — analyst, investor, student, policymaker?
    - It's meant for analysts/investors. But anyone can take a look to see how the fed responded to market movements, and how market responded to fed movements; essentially, how monetary policy interacts with markets over time.
32. Why focus on the **Fed SOMA** dataset specifically — what insight or skill were you trying to demonstrate?
    - Personally I had an interest in the fed soma dataset already, for stock and investing purposes. Automating it and making it into a study tool as well as a portfolio piece was a natural extension of that once I decided to learn coding
33. What’s the long-term vision — extend into real-time updates, deeper analytics, or integrate with financial APIs?
    - If I was to build onto this, yes it would provide real-time updates, or be hosted on a server that would update weekly. Analytics could be integrated but would require alot of domain knowledge to have actual meaningful insights. At this point though, not sure it it is the way I want to go since it is reaching to a point where it would become a product that wouldn't really belong on a repo, as it would have tangible financial insights that is worth money. 
34. Why did you choose to annotate the code so heavily — was this part of your learning strategy?
    - Yes, that was why. It was initially created with vibe coding, and gradually shifted as I tried to understand the code. Eventually I asked ChatGPT to just annotate the entire code line by line. I plan to create a branch with the annotated code, and have the main repo be a lot more cleaner with less annotations.
35. What are the biggest lessons learned during the walkthrough — technical or conceptual?
    - Mainly the exposure to the processes themselves as well as all the different elements of the pipeline was the main takeaway. At first I wouldn't understand 80% of the code but now I would say if I look at it slowly I can understand all of the code. 

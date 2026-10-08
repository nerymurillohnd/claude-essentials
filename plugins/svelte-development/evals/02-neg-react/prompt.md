---
description: "React question: no Svelte skill, no Svelte docs, a React answer."
tags: [pilot]
runs: 3
max_turns: 5
timeout_seconds: 120
allowed_tools: [Read, Skill, ToolSearch]
---

My React search results don't update when I type a new query. What's wrong?

```jsx
import { useEffect, useState } from "react";

export function SearchResults({ query }) {
  const [results, setResults] = useState([]);

  useEffect(() => {
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
      .then((response) => response.json())
      .then(setResults);
  }, []);

  return (
    <ul>
      {results.map((result) => (
        <li key={result.id}>{result.title}</li>
      ))}
    </ul>
  );
}
```

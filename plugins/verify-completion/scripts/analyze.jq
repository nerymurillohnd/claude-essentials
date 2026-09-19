# verify-completion: analyze the reply that ends a turn.
#
# Input:  the Stop hook payload (JSON).
# Output: {"claims": [string], "record": {"present": bool, "verdict": string,
#          "errors": [string]}, "stop_hook_active": bool}
#
# Compatible with jq 1.6+: no builtins newer than 1.6 (trim, abs, ...) and no
# match offsets (byte-based on 1.6); only anchored captures.

# ---------------------------------------------------------------- helpers ---

def lines: split("\n") | map(sub("\r$"; ""));

# Drop fenced code blocks (``` or ~~~) so quoted code never reads as a claim.
def unfenced:
  reduce .[] as $l ({out: [], fence: false};
    if ($l | (contains("```") or contains("~~~")) and test("^\\s{0,3}(```|~~~)")) then .fence = (.fence | not)
    elif .fence then .
    else .out += [$l]
    end)
  | .out;

# Markdown noise that sits between words: emphasis markers and inline code.
def plain: gsub("`[^`]*`"; " ") | gsub("\\*\\*|__|(?<![A-Za-z0-9])[*_]|[*_](?![A-Za-z0-9])"; "");

def words_before($n): [splits("\\s+") | select(length > 0)] | .[-$n:] | join(" ");

# ------------------------------------------------------- claim detection ---

# Phrases that present work as finished. English and Spanish, case-insensitive.
def claim_patterns: [
  # tests / checks green
  "\\b(?:all|every)\\s+(?:the\\s+|of\\s+the\\s+)?(?:tests?|checks?|specs?|suites?)\\s+(?:now\\s+)?(?:pass(?:es|ed)?|are\\s+(?:passing|green)|(?:is|are)\\s+green)\\b",
  "\\b(?:tests?|checks?|ci|build|pipeline|suite)\\s+(?:is|are)\\s+(?:now\\s+)?(?:all\\s+)?(?:green|passing)\\b",
  # "<it> is done / ready / fixed ..."
  "\\b(?:is|are|am|'s|'re|'m|has\\s+been|have\\s+been)\\s+(?:now\\s+)?(?:fully\\s+|all\\s+|completely\\s+)?(?:done|complete|completed|finished|fixed|resolved|verified|ready|working(?!\\s+on\\b))\\b(?!\\s+(?:to\\s+(?:start|begin|continue|go)|for\\s+(?:your\\s+)?(?:input|feedback|questions?|instructions?)))",
  "\\bready\\s+(?:to|for)\\s+(?:be\\s+)?(?:merge[ds]?|merging|commit(?:ted)?|ship(?:ped)?|deploy(?:ed|ment)?|release[ds]?|review|push(?:ed)?|hand[\\s-]?off|production|prod|pr|pull\\s+request)\\b",
  "\\b(?:successfully|fully)\\s+(?:implemented|completed|fixed|deployed|verified|resolved|tested|working|functional)\\b",
  "^\\s*(?:all\\s+)?(?:done|finished|complete|completed)\\s*(?:[.!:,]|$)",
  "\\b(?:it|this|everything|that)\\s+(?:now\\s+)?works\\b",
  "\\bi(?:'ve|\\s+have)\\s+(?:now\\s+)?(?:completed|finished|fixed|verified|resolved)\\b",
  "\\b(?:lgtm|ship\\s+it|good\\s+to\\s+go|all\\s+set|all\\s+green)\\b",
  # Spanish
  "\\b(?:las\\s+|los\\s+|todas\\s+las\\s+|todos\\s+los\\s+)?(?:pruebas|tests|checks|comprobaciones|validaciones)\\s+(?:ya\\s+)?(?:pasan|pasaron|están\\s+en\\s+verde|están\\s+pasando|quedaron\\s+en\\s+verde)\\b",
  "(?:^|\\s)(?:está|están|quedó|quedaron|queda|quedan|ha\\s+quedado|han\\s+quedado)\\s+(?:ya\\s+)?(?:todo\\s+)?(?:completamente\\s+|totalmente\\s+)?(?:list[oa]s?|terminad[oa]s?|complet[oa]s?|completad[oa]s?|verificad[oa]s?|funcionando|resuelt[oa]s?|arreglad[oa]s?|corregid[oa]s?|implementad[oa]s?)(?=$|[\\s.,;:!)])",
  "(?:^|\\s)list[oa]s?\\s+para\\s+(?:el\\s+|la\\s+|un\\s+|una\\s+|hacer\\s+)?(?:merge|mergear|fusionar|commit|confirmar|entregar|entrega|revisión|revision|revisar|producción|produccion|desplegar|despliegue|publicar|push|pr|pull\\s+request|release)\\b",
  "^\\s*¡?\\s*(?:list[oa]|hecho|terminado|completado)\\s*(?:[.!:,]|$)",
  "(?:^|\\s)ya\\s+quedó(?=$|[\\s.,;:!)])",
  "(?:^|\\s)todo\\s+(?:está\\s+|quedó\\s+)?(?:listo|en\\s+verde|terminado|funcionando|resuelto|correcto)(?=$|[\\s.,;:!)])",
  "(?:^|\\s)funcionan?\\s+(?:correctamente|perfectamente|como\\s+se\\s+esperaba)(?=$|[\\s.,;:!)])",
  "(?:^|\\s)(?:completé|terminé|arreglé|corregí|verifiqué|resolví)(?=$|[\\s.,;:!)])",
  "(?:^|\\s)(?:con\\s+éxito|exitosamente)(?=$|[\\s.,;:!)])"
];

# The subset that presents the whole piece of work as finished. Partial results
# ("the parser bug is fixed, the e2e run is blocked") are honest in a NOT
# VERIFIED reply; these are not.
def global_claim_patterns: [
  "\\b(?:all|every)\\s+(?:the\\s+|of\\s+the\\s+)?(?:tests?|checks?|specs?|suites?)\\s+(?:now\\s+)?(?:pass(?:es|ed)?|are\\s+(?:passing|green)|(?:is|are)\\s+green)\\b",
  "\\bready\\s+(?:to|for)\\s+(?:be\\s+)?(?:merge[ds]?|merging|commit(?:ted)?|ship(?:ped)?|deploy(?:ed|ment)?|release[ds]?|review|push(?:ed)?|hand[\\s-]?off|production|prod|pr|pull\\s+request)\\b",
  "\\b(?:everything|it\\s+all|all\\s+of\\s+it|the\\s+(?:work|task|change|changes|feature|implementation|fix|pr|branch))\\s+(?:is|are|'s|has\\s+been|have\\s+been)\\s+(?:now\\s+)?(?:fully\\s+|all\\s+)?(?:done|complete|completed|finished|ready|verified)\\b",
  "^\\s*(?:all\\s+)?(?:done|finished|complete|completed)\\s*(?:[.!:,]|$)",
  "\\bi(?:'m|\\s+am)\\s+(?:all\\s+)?(?:done|finished)\\b",
  "\\b(?:lgtm|ship\\s+it|good\\s+to\\s+go|all\\s+set|all\\s+green)\\b",
  "(?:^|\\s)list[oa]s?\\s+para\\s+(?:el\\s+|la\\s+|un\\s+|una\\s+|hacer\\s+)?(?:merge|mergear|fusionar|commit|confirmar|entregar|entrega|revisión|revision|revisar|producción|produccion|desplegar|despliegue|publicar|push|pr|pull\\s+request|release)\\b",
  "^\\s*¡?\\s*(?:list[oa]|hecho|terminado|completado)\\s*(?:[.!:,]|$)",
  "(?:^|\\s)ya\\s+quedó(?=$|[\\s.,;:!)])",
  "(?:^|\\s)todo\\s+(?:está\\s+|quedó\\s+)?(?:listo|en\\s+verde|terminado|funcionando|resuelto|correcto)(?=$|[\\s.,;:!)])",
  "(?:^|\\s)(?:todas\\s+las\\s+pruebas|todos\\s+los\\s+tests)\\s+(?:ya\\s+)?(?:pasan|pasaron|están\\s+en\\s+verde)\\b"
];

# Words that, shortly before a match, make it negated or conditional.
def negation:
  "(?:^|[\\s,(])(?:not|no|never|nor|cannot|can't|won't|isn't|aren't|wasn't|weren't|haven't|hasn't|don't|doesn't|didn't|unless|until|if|when|whether|nunca|ni|si|cuando|hasta|sin|tampoco)(?:$|[\\s,.;:])|n't(?:$|\\s)";

def sentences: [splits("(?<=[.!?;])\\s+")] | map(select(test("\\S")));

def question: test("\\?\\s*$") or test("^\\s*¿");

def claims_in($s; $patterns):
  if ($s | question) then empty
  else
    $patterns[] as $p
    | ($s | capture("^(?<pre>.*?)(?<hit>" + $p + ")"; "i")?) as $m
    | select($m != null)
    | select(($m.pre | words_before(6) | test(negation; "i")) | not)
    | $m.hit | gsub("^\\s+|\\s+$"; "")
  end;

# One pass over the whole reply with every pattern at once; line-start anchors
# also match after a newline there.
def any_pattern($patterns):
  $patterns | map(sub("^\\^"; "(?:^|(?<=\\n))")) | "(?:" + join(")|(?:") + ")";

# jq compiles a regex on every call and builds match objects slowly, so the
# whole reply gets one boolean test; only then are the closing 300 lines outside
# code blocks checked line by line, stopping after three claims. The closing
# lines carry the conclusion, and three examples are enough to report.
def claims($patterns):
  any_pattern($patterns) as $any
  | if join("\n") | test($any; "i") | not then []
    else
      unfenced | .[-300:]
      | [ limit(3; .[] | select(test($any; "i")) | select(test("^\\s*>") | not)
          | plain | sentences[] as $s | claims_in($s; $patterns)) ]
      | unique
    end;

# ------------------------------------------------------ record validation ---

# A Markdown or bold heading may carry a short prefix ("### 🔍 Final
# verification record"); a plain-text heading must be the whole line, so prose
# that mentions "the Verification record above" never starts a record.
def record_heading:
  "^\\s{0,3}(?:(?<hashes>#{1,6})\\s*(?:\\*\\*|__)?|\\*\\*|__)[^\\p{L}\\p{N}\\n]{0,8}(?:(?:final|full|the)\\s+)?(?:verification\\s+record|registro\\s+de\\s+verificaci[oó]n)\\b|^\\s{0,3}(?:verification\\s+record|registro\\s+de\\s+verificaci[oó]n)\\s*:?\\s*$";

# true for each line that is a code fence or inside one.
def fence_mask:
  reduce .[] as $l ({mask: [], fence: false};
    if ($l | (contains("```") or contains("~~~")) and test("^\\s{0,3}(```|~~~)")) then .mask += [true] | .fence = (.fence | not)
    else .mask += [.fence]
    end)
  | .mask;

def norm: gsub("\\*\\*|__"; "") | sub("^[\\s|>*+-]+"; "");

def meaningful: gsub("[^\\p{L}\\p{N}]"; "") | length;

# The record is the last heading that names it, up to the next heading of the
# same or a higher level (any heading if it was bold or plain text). Returns
# {top, stop} line indexes (heading included, stop excluded), or null.
def record_range:
  . as $all
  | fence_mask as $mask
  | [range(0; $all | length)
     | select($mask[.] | not)
     | select($all[.] | ascii_downcase | contains("verification record") or contains("registro de verificaci"))
     | select($all[.] | test(record_heading; "i"))] as $starts
  | if ($starts | length) == 0 then null
    else
      $starts[-1] as $i
      | ($all[$i] | capture(record_heading; "i").hashes // "" | length) as $level
      | [range($i + 1; $all | length)] as $rest
      | ([ $rest[] | select($mask[.] | not) | select($all[.] | contains("#")) | select(
            ($all[.] | (capture("^\\s{0,3}(?<h>#{1,6})\\s")? | .h) // null) as $h
            | $h != null and ($level == 0 or ($h | length) <= $level)
          ) ] | first // ($all | length)) as $stop
      | {top: $i, stop: $stop}
    end;

def gate_line:
  norm
  | capture("^(?:gate\\s*)?(?<n>[1-6])(?:\\s*[.):|-]|\\s)\\s*(?<rest>.*)$"; "i")?
  | . as $g
  | ($g.rest | capture("^(?<pre>.*?)(?<![A-Za-z/])(?<st>PASS|FAIL|N/A|BLOCKED)(?![A-Za-z/])(?<post>.*)$")?) as $s
  | select($s != null)
  | {n: ($g.n | tonumber), status: $s.st,
     note: ($s.post | gsub("^[\\s|:—–-]+|[\\s|]+$"; ""))};

def record($range):
  (if $range == null then null else .[$range.top + 1:$range.stop] end) as $raw
  | (if $range == null then null else (fence_mask | .[$range.top + 1:$range.stop]) end) as $mask
  | if $raw == null then {present: false, verdict: "", errors: []}
    else
      # Lines inside code blocks are evidence, never structure.
      [ range(0; $raw | length) | select($mask[.] | not) | $raw[.] ] as $rec
      | ($rec | map(norm)) as $n
      | ([ range(0; $n | length) as $k
           | ($n[$k] | capture("^(?:requirements?|requisitos?|acceptance\\s+criteria|criterios\\s+de\\s+aceptación)\\s*[:|]\\s*(?<t>.*)$"; "i")? | .t) as $t
           # "Requirement:" alone on its line: the text is on the next one.
           | if ($t | meaningful) > 0 then $t
             else ([ $n[$k + 1:][] | select(test("\\S")) ] | first // "") end
         ] | first // null) as $req
      | ([ $n[] | gsub("`"; "") | (capture("^(?i:verdict|veredicto)\\s*[:|—–-]?\\s*(?<v>(?i:not\\s+verified|verified))(?![A-Za-z])")? | .v) | ascii_upcase | gsub("\\s+"; " ") ] | last // "") as $verdict
      # Gates sit at the start of a line; indented numbered sub-lists are detail.
      | [ $rec[] | select(test("^ {0,1}\\S")) | gate_line ] as $gates
      | ($rec | join("\n") | test("`[^`\\n]+`|```|~~~")) as $artifact
      | {present: true, verdict: $verdict,
         errors: (
           [ if $req == null then "missing a \"Requirement:\" line stating what was asked"
             elif ($req | meaningful) < 12 then "the Requirement line is too short to say what was asked"
             else empty end ]
           + [ if $verdict == "" then "missing a \"Verdict: VERIFIED\" or \"Verdict: NOT VERIFIED\" line" else empty end ]
           + [ range(1; 7) as $k
               | [ $gates[] | select(.n == $k) ] as $g
               | if ($g | length) == 0 then "gate \($k) is missing (a line like \"\($k). <gate>: PASS|FAIL|N/A|BLOCKED — <evidence or reason>\")"
                 elif ($g | length) > 1 then "gate \($k) appears \($g | length) times"
                 elif ($g[0].note | meaningful) < 12 then "gate \($k) (\($g[0].status)) has no evidence or reason after its status"
                 else empty end ]
           + ( if $verdict == "VERIFIED" then
                 [ $gates[] | select(.status == "FAIL" or .status == "BLOCKED")
                   | "verdict is VERIFIED but gate \(.n) is \(.status)" ]
                 + [ $gates[] | select(.status == "N/A" and (.n == 1 or .n == 2 or .n == 4 or .n == 6))
                     | "gate \(.n) always applies; it cannot be N/A in a VERIFIED record" ]
                 + [ if $artifact then empty
                     else "a VERIFIED record needs at least one re-runnable artifact in `code` (a command, path, or output)" end ]
               else [] end ))}
    end;

# ------------------------------------------------------------------ main ---

(.stop_hook_active == true) as $active
| (.last_assistant_message // "") as $msg
| if ($msg | type) != "string" then {claims: [], record: {present: false, verdict: "", errors: []}}
  else
    ($msg | lines) as $lines
    | ($lines | record_range) as $range
    # Claims are looked for outside the record: its evidence lines say "PASS".
    | (if $range == null then $lines else $lines[:$range.top] + $lines[$range.stop:] end) as $prose
    | {claims: ($prose | claims(claim_patterns)), record: ($lines | record($range))}
    # Verification is what makes "done" true: a reply can't present the work as
    # finished while its own record says it isn't verified.
    | if .record.present and .record.verdict == "NOT VERIFIED" then
        ($prose | claims(global_claim_patterns)) as $global
        | if ($global | length) > 0 then
            .record.errors += ["the reply presents the work as finished (\($global | map("\"" + . + "\"") | join(", "))) while its verdict is NOT VERIFIED; say what is verified and what is not, without calling the work done"]
          else . end
      else . end
  end
| .stop_hook_active = $active

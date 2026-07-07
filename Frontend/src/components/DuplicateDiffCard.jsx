import React from "react";

const METHOD_LABELS = {
  exact: "EXACT MATCH",
  sha256: "SHA-256",
  md5: "MD5",
  levenshtein: "LEVENSHTEIN",
  jaccard: "JACCARD",
  cosine: "COSINE",
  soundex: "SOUNDEX",
  metaphone: "METAPHONE",
};

/**
 * DuplicateDiffCard
 * ==================
 * The signature element of this app: renders a duplicate finding the way
 * a code review tool renders a diff. The matched field is called out, the
 * algorithm and confidence are stamped in monospace (like a commit hash),
 * and the resolution actions live directly below, right where the
 * decision needs to be made.
 */
export default function DuplicateDiffCard({ duplicate, onResolve }) {
  const scorePct = Math.round(duplicate.similarity_score * 100);

  return (
    <div className="diff-card mb-3">
      <div className="diff-header">
        <span>
          row <strong className="score">#{duplicate.new_row_number}</strong> vs existing record{" "}
          <strong className="score">#{duplicate.existing_record_ref}</strong>
        </span>
        <span>
          <span className="badge-soft badge-amber" style={{ marginRight: 8 }}>
            {METHOD_LABELS[duplicate.detection_method] || duplicate.detection_method}
          </span>
          <span className="score">{scorePct}% match</span>
        </span>
      </div>

      <div className="diff-body">
        <div className="diff-col">
          <div className="col-label">Matched field</div>
          <div className="diff-field differs">
            <span className="field-name">{duplicate.match_field}</span>
          </div>
        </div>
        <div className="diff-col">
          <div className="col-label">Status</div>
          <span className={`badge-soft ${duplicate.status === "pending" ? "badge-neutral" : "badge-teal"}`}>
            {duplicate.status}
          </span>
        </div>
      </div>

      {duplicate.status === "pending" && (
        <div className="diff-actions">
          <button className="btn-outline-quiet" onClick={() => onResolve(duplicate.id, "merge")}>Merge</button>
          <button className="btn-outline-quiet" onClick={() => onResolve(duplicate.id, "replace")}>Replace</button>
          <button className="btn-outline-quiet" onClick={() => onResolve(duplicate.id, "keep_latest")}>Keep latest</button>
          <button className="btn-outline-quiet" onClick={() => onResolve(duplicate.id, "keep_oldest")}>Keep oldest</button>
          <button className="btn-outline-quiet" onClick={() => onResolve(duplicate.id, "ignore")}>Ignore</button>
          <button className="btn-outline-quiet" style={{ color: "var(--red)", borderColor: "var(--red-soft)" }} onClick={() => onResolve(duplicate.id, "delete")}>
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

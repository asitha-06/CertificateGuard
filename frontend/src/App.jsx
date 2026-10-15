
import { useState } from "react";
import { api } from "./services/api";
import "./styles.css";

function show(value) {
  return value === undefined || value === null || value === ""
    ? "Not available"
    : String(value);
}

function getPrediction(data) {
  const value = String(data?.prediction || "").toLowerCase();

  if (
    value.includes("tamper") ||
    value.includes("fake") ||
    value.includes("forg")
  ) {
    return "tampered";
  }

  if (
    value === "original" ||
    value === "authentic" ||
    value === "genuine"
  ) {
    return "original";
  }

  return "unknown";
}

function getBlockchain(data) {
  const chain = data?.blockchain || {};

  return {
    network: chain.network || "Sepolia",
    registered: chain.record_found === true,
    hashMatches: chain.hash_matches === true,
    status: chain.status || "unknown",
    message: chain.message || "Blockchain status is unavailable.",
    certificateId: chain.certificate_id || null,
  };
}

function getBlockchainExplanation(blockchain) {
  if (!blockchain.registered) {
    return "No registered blockchain record was found for the certificate ID used in this lookup. Its on-chain integrity could not be confirmed.";
  }

  if (blockchain.hashMatches) {
    return "The uploaded file's SHA-256 hash matches the hash stored in the registered blockchain record. This confirms a hash match for this record, but does not independently verify the certificate's personal details.";
  }

  return "A blockchain record was found, but its stored hash differs from the uploaded file's SHA-256 hash. The file does not match that registered record.";
}

export default function App() {
  const [file, setFile] = useState(null);
  const [certificateId, setCertificateId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function verifyCertificate(event) {
    event.preventDefault();

    if (!file) {
      setError("Please select a certificate image or PDF first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await api.verify(file, certificateId);
      setResult(data);
    } catch (err) {
      setError(
        err.message || "Unable to connect to the verification server."
      );
    } finally {
      setLoading(false);
    }
  }

  const prediction = result ? getPrediction(result) : "unknown";
  const details = result?.details || {};
  const blockchain = result ? getBlockchain(result) : null;
  const fieldAnalysis = result?.field_analysis || {};
  const fields = fieldAnalysis.fields || {};
  const flaggedFields =
    result?.tampered_fields || fieldAnalysis.tampered_fields || [];
  const referenceAvailable =
    fieldAnalysis.reference_comparison_available === true;

  let verdict = "Verification Inconclusive";
  let verdictMessage =
    "The available checks are insufficient to establish document authenticity.";

  if (prediction === "tampered") {
    verdict = "Potential Tampering Detected";
    verdictMessage =
      "The AI model flagged this document as potentially altered. Compare it with a trusted original before making a decision.";
  } else if (prediction === "original") {
    verdict = "Certificate Appears Original";
    verdictMessage =
      "The AI model classified this document as original. This result alone does not confirm that the certificate is genuine.";
  }

  return (
    <main className="page">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CertificateGuard home">
          <span className="brand-mark">✓</span>
          <span>CertificateGuard</span>
        </a>
        <span className="topbar-label">Certificate Verification</span>
      </header>

      <section className="hero">
        <div className="eyebrow">SIMPLE · SECURE · TRANSPARENT</div>
        <h1>Verify a Certificate</h1>
        <p>
          Upload a certificate to review its classification, extracted
          details, file hash, and blockchain verification status.
        </p>
      </section>

      <section className="verify-card">
        <form onSubmit={verifyCertificate}>
          <label className="field-label" htmlFor="certificate-file">
            Certificate document
          </label>

          <label className={`upload-area ${file ? "has-file" : ""}`}>
            <input
              id="certificate-file"
              type="file"
              accept=".png,.jpg,.jpeg,.webp,.pdf"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null);
                setResult(null);
                setError("");
              }}
            />

            <span className="upload-icon">↑</span>
            <strong>
              {file ? file.name : "Choose a certificate file"}
            </strong>

            <span className="upload-hint">
              {file
                ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Selected`
                : "PNG, JPG, WEBP or PDF"}
            </span>

            <span className="choose-button">Browse files</span>
          </label>

          <label className="field-label" htmlFor="certificate-id">
            Certificate number <span className="optional">(optional)</span>
          </label>

          <input
            id="certificate-id"
            className="text-input"
            type="text"
            placeholder="Enter the registered certificate number"
            value={certificateId}
            onChange={(event) => setCertificateId(event.target.value)}
          />

          <button className="verify-button" type="submit" disabled={loading}>
            {loading ? "Verifying certificate..." : "Verify Certificate"}
          </button>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
        </form>
      </section>

      {result && (
        <section className="results">
          <div className={`result-banner ${prediction}`}>
            <div>
              <span className="result-overline">VERIFICATION RESULT</span>
              <h2>{verdict}</h2>
              <p>{verdictMessage}</p>
              <p>
                Model confidence:{" "}
                {typeof result.confidence === "number"
                  ? `${(result.confidence * 100).toFixed(2)}%`
                  : "Not available"}
              </p>
            </div>

            <span className="result-symbol">
              {prediction === "tampered"
                ? "!"
                : prediction === "original"
                  ? "✓"
                  : "?"}
            </span>
          </div>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>Certificate Details</h3>
                <p>
                  Information extracted from the uploaded document using OCR
                </p>
              </div>
            </div>

            <div className="details-grid">
              {[
                ["Certificate Holder", details.student_name],
                ["College / Institution", details.institution],
                ["Degree / Course", details.course_name],
                ["Certificate Number", details.certificate_id],
                ["Issue Date (extracted)", details.issue_date],
                ["Uploaded File", result.filename || file?.name],
              ].map(([label, value]) => (
                <div className="detail-item" key={label}>
                  <span>{label}</span>
                  <strong>{show(value)}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>Trusted Reference Comparison</h3>
                <p>
                  Extracted text must be checked against a trusted record to
                  confirm its accuracy.
                </p>
              </div>
            </div>

            {referenceAvailable ? (
              <div className="notice">
                <strong>Reference comparison available</strong>
                <p>Review the individual field results below.</p>
              </div>
            ) : (
              <div className="notice">
                <strong>Not verified against a trusted reference</strong>
                <p>
                  The system has extracted text but has not confirmed the name,
                  certificate number, course, institution, or date against a
                  trusted record.
                </p>
              </div>
            )}

            {Object.keys(fields).length > 0 && (
              <div className="details-grid">
                {Object.entries(fields).map(([key, field]) => (
                  <div className="detail-item" key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>{show(field?.value)}</strong>
                    <span>{show(field?.status)}</span>
                  </div>
                ))}
              </div>
            )}

            {Array.isArray(flaggedFields) && flaggedFields.length > 0 ? (
              <div className="flagged-list">
                {flaggedFields.map((field, index) => (
                  <div className="flagged-item" key={`${field}-${index}`}>
                    <span className="flag-dot">!</span>
                    <div>
                      <strong>{String(field).replaceAll("_", " ")}</strong>
                      <p>
                        Flagged by the verification service for further review.
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="integrity-note">
                No specific altered fields were identified. This does not prove
                that every field is correct.
              </p>
            )}
          </section>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>Blockchain Integrity Check</h3>
                <p>Checks against an existing on-chain record</p>
              </div>
              <span className="network-pill">{blockchain.network}</span>
            </div>

            <div className="integrity-grid">
              <div className="integrity-item">
                <span>Registered Record</span>
                <strong>
                  {blockchain.registered ? "Found" : "Not found"}
                </strong>
              </div>

              <div className="integrity-item">
                <span>On-chain Hash Comparison</span>
                <strong>
                  {!blockchain.registered
                    ? "Not available"
                    : blockchain.hashMatches
                      ? "Match"
                      : "Mismatch"}
                </strong>
              </div>

              <div className="integrity-item">
                <span>Local Hash Database</span>
                <strong>{show(result.hash_database?.status)}</strong>
              </div>
            </div>

            {blockchain.certificateId && (
              <p className="integrity-note">
                Certificate ID checked: <strong>{blockchain.certificateId}</strong>
              </p>
            )}

            <p className="integrity-note">{blockchain.message}</p>
            <p className="integrity-note">
              {getBlockchainExplanation(blockchain)}
            </p>
          </section>

          {result.sha256 && (
            <section className="hash-box">
              <span>Uploaded File SHA-256</span>
              <code>{result.sha256}</code>
            </section>
          )}
        </section>
      )}

      <footer className="footer">
        CertificateGuard · AI classification, OCR, hashing and blockchain checks
      </footer>
    </main>
  );
}

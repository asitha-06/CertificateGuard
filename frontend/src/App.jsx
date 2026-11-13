import React, { useState } from "react";
import { api } from "./services/api";
import "./styles.css";

function show(value) {
  return value === undefined || value === null || value === ""
    ? "Not available"
    : String(value);
}

function getPrediction(data) {
  const value = String(data?.prediction || "").toLowerCase();

  if (value.includes("tamper") || value.includes("fake") || value.includes("forg")) {
    return "tampered";
  }

  if (["original", "authentic", "genuine"].includes(value)) {
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
    certificateId: chain.certificate_id || data?.certificate_id || null,
  };
}

function StatusPill({ status }) {
  const normalized = String(status || "").toLowerCase();
  let className = "status-neutral";
  if (["safe", "match", "verified", "original", "success"].includes(normalized)) {
    className = "status-safe";
  } else if (["unsafe", "mismatch", "tampered", "error"].includes(normalized)) {
    className = "status-unsafe";
  } else if (["not detected", "needs_reference", "not_checked"].includes(normalized)) {
    className = "status-pending";
  }
  return <span className={`status-pill ${className}`}>{show(status).replaceAll("_", " ")}</span>;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function verifyCertificate(event) {
    event.preventDefault();

    if (!file) {
      setError("Please select a certificate image or PDF first.");
      return;
    }
    if (!registrationNumber.trim()) {
      setError("Please enter the student's registration number.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await api.verify(file, registrationNumber);
      setResult(data);
    } catch (err) {
      setError(err.message || "Unable to connect to the verification server.");
    } finally {
      setLoading(false);
    }
  }

  const prediction = result ? getPrediction(result) : "unknown";
  const details = result?.details || {};
  const blockchain = result ? getBlockchain(result) : null;
  const fields = result?.field_analysis?.fields || {};
  const flaggedFields = result?.tampered_fields || result?.field_analysis?.tampered_fields || [];
  const referenceAvailable = result?.field_analysis?.reference_comparison_available === true;
  const confidence = typeof result?.confidence === "number"
    ? `${(result.confidence * 100).toFixed(2)}%`
    : "Not available";

  const verdict = prediction === "original"
    ? "AI classified as Original"
    : prediction === "tampered"
      ? "Potential Tampering Detected"
      : "Verification Inconclusive";

  const verdictMessage = prediction === "original"
    ? "The AI model classified this document as original. This alone does not prove the certificate is genuine."
    : prediction === "tampered"
      ? "The AI model flagged this document as potentially altered. Compare it with a trusted original."
      : "The available checks are insufficient to establish document authenticity.";

  return (
    <main className="page">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CertificateGuard home">
          <span className="brand-mark">✓</span>
          <span>CertificateGuard</span>
        </a>
        <span className="topbar-label">AI · OCR · Blockchain Verification</span>
      </header>

      <section className="hero">
        <div className="eyebrow">SIMPLE · SECURE · TRANSPARENT</div>
        <h1>Verify a Certificate</h1>
        <p>Upload a certificate and enter its registration number to review AI classification, extracted details, field comparison, hashing and blockchain status.</p>
      </section>

      <section className="verify-card">
        <form onSubmit={verifyCertificate}>
          <label className="field-label" htmlFor="certificate-file">Certificate document</label>
          <label className={`upload-area ${file ? "has-file" : ""}`}>
            <input
              id="certificate-file"
              type="file"
              accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.pdf"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null);
                setResult(null);
                setError("");
              }}
            />
            <span className="upload-icon">↑</span>
            <strong>{file ? file.name : "Choose a certificate file"}</strong>
            <span className="upload-hint">
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Selected` : "PNG, JPG, WEBP or PDF · Maximum 20 MB"}
            </span>
            <span className="choose-button">Browse files</span>
          </label>

          <label className="field-label" htmlFor="registration-number">Student Registration Number</label>
          <input
            id="registration-number"
            className="text-input"
            type="text"
            placeholder="Example: 23BCE20239"
            value={registrationNumber}
            onChange={(event) => setRegistrationNumber(event.target.value.toUpperCase())}
            autoComplete="off"
          />

          <button className="verify-button" type="submit" disabled={loading}>
            {loading ? "Verifying certificate..." : "Verify Certificate"}
          </button>

          {error && <div className="error-message" role="alert">{error}</div>}
        </form>
      </section>

      {result && (
        <section className="results">
          <div className={`result-banner ${prediction}`}>
            <div>
              <span className="result-overline">1 · AI CLASSIFICATION</span>
              <h2>{verdict}</h2>
              <p>{verdictMessage}</p>
              <div className="confidence-row">
                <span>Confidence score</span>
                <strong>{confidence}</strong>
              </div>
            </div>
            <span className="result-symbol">
              {prediction === "tampered" ? "!" : prediction === "original" ? "✓" : "?"}
            </span>
          </div>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>2 · Extracted Certificate Details</h3>
                <p>Text recognised from the uploaded certificate using Tesseract OCR.</p>
              </div>
              <StatusPill status={result.ocr_status || "unknown"} />
            </div>
            <div className="details-grid">
              {[
                ["Student Name", details.student_name],
                ["Registration Number (OCR)", details.certificate_id],
                ["Course / Programme", details.course_name],
                ["Institution", details.institution],
                ["Issue Date", details.issue_date],
                ["Uploaded File", result.filename || file?.name],
              ].map(([label, value]) => (
                <div className="detail-item" key={label}>
                  <span>{label}</span>
                  <strong>{show(value)}</strong>
                </div>
              ))}
            </div>
            <p className="integrity-note">
              OCR preprocessing: {show(result.ocr_method)}. If a value is not detected, check the image quality and the original certificate.
            </p>
          </section>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>3 · Field-by-Field Verification</h3>
                <p>Safe/Unsafe labels require trusted reference details for comparison.</p>
              </div>
              <StatusPill status={referenceAvailable ? "Reference available" : "Needs reference"} />
            </div>

            {!referenceAvailable && (
              <div className="notice">
                <strong>Trusted field comparison is not configured yet</strong>
                <p>The current records map registration numbers to certificate IDs and hashes. They do not contain trusted names, courses, institutions or issue dates. Those fields are shown as extracted, not incorrectly labelled Safe or Unsafe.</p>
              </div>
            )}

            {Object.keys(fields).length > 0 ? (
              <div className="field-comparison-list">
                {Object.entries(fields).map(([key, field]) => (
                  <div className="field-comparison-item" key={key}>
                    <div>
                      <strong>{key.replaceAll("_", " ")}</strong>
                      <span>{show(field?.value)}</span>
                    </div>
                    <StatusPill status={field?.status || "Not compared"} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="integrity-note">No field comparison data was returned by the backend.</p>
            )}

            {Array.isArray(flaggedFields) && flaggedFields.length > 0 && (
              <div className="flagged-list">
                {flaggedFields.map((field, index) => (
                  <div className="flagged-item" key={`${field}-${index}`}>
                    <span className="flag-dot">!</span>
                    <div><strong>{String(field).replaceAll("_", " ")}</strong><p>Flagged by the verification service for review.</p></div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="result-section">
            <div className="section-heading">
              <div>
                <h3>4 · Hash & Blockchain Verification</h3>
                <p>Checks the original uploaded file against its registered record.</p>
              </div>
              <span className="network-pill">{blockchain.network}</span>
            </div>

            <div className="integrity-grid">
              <div className="integrity-item">
                <span>Local Hash Database</span>
                <strong>{show(result.hash_database?.status)}</strong>
              </div>
              <div className="integrity-item">
                <span>Blockchain Record</span>
                <strong>{blockchain.registered ? "Found" : "Not found"}</strong>
              </div>
              <div className="integrity-item">
                <span>On-chain Hash Comparison</span>
                <strong>{!blockchain.registered ? "Not available" : blockchain.hashMatches ? "Match" : "Mismatch"}</strong>
              </div>
              <div className="integrity-item">
                <span>Certificate ID checked</span>
                <strong>{show(blockchain.certificateId || result.certificate_id)}</strong>
              </div>
            </div>

            <p className="integrity-note">{blockchain.message}</p>
            <p className="integrity-note">A hash match confirms that the uploaded file matches the hash in that blockchain record. It does not independently validate personal details.</p>
          </section>

          {result.sha256 && (
            <section className="hash-box">
              <span>SHA-256 of Original Uploaded File</span>
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

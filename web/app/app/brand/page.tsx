"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type BrandProfile, type Dashboard } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

export default function BrandPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    fetchDashboard(token)
      .then((data) => { if (!ignore) setDashboard(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [token]);

  useEffect(() => {
    if (!token || !project) return;
    let ignore = false;
    apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {}, token)
      .then((data) => { if (!ignore) setBrand(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [project, token]);

  async function fillFromWebsite() {
    if (!token || !project || !brand?.website_url) return;
    setAnalyzing(true);
    try {
      const analyzed = await apiRequest<BrandProfile>(`/v1/brand/${project.id}/analyze`, {
        method: "POST",
        body: JSON.stringify({ website_url: brand.website_url })
      }, token);
      setBrand(analyzed);
      setMessage("Website details filled in.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not read the website.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function analyzeWebsite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await fillFromWebsite();
  }

  async function saveBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !project || !brand) {
      return;
    }
    try {
      const payload = await apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {
        method: "PUT",
        body: JSON.stringify(brand)
      }, token);
      setBrand(payload);
      setMessage("Product details saved.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save product details.");
    }
  }

  if (!brand) {
    return <section className="card"><div className="empty-state">Go to Home and create a business first.</div></section>;
  }

  return (
    <div className="split-grid">
      <form className="card" onSubmit={saveBrand}>
        <div className="eyebrow">Your product</div>
        <h2>Tell us what you sell</h2>
        <p>Keep this simple. Plain English works best.</p>
        {message ? <div className="notice">{message}</div> : null}
        <label className="field">
          <span>Business name</span>
          <input value={brand.brand_name} onChange={(event) => setBrand({ ...brand, brand_name: event.target.value })} required />
        </label>
        <label className="field">
          <span>Website URL</span>
          <input value={brand.website_url ?? ""} onChange={(event) => setBrand({ ...brand, website_url: event.target.value })} />
        </label>
        <label className="field">
          <span>What do you sell?</span>
          <textarea value={brand.product_summary ?? ""} onChange={(event) => setBrand({ ...brand, product_summary: event.target.value })} />
        </label>
        <label className="field">
          <span>Who is it for?</span>
          <textarea value={brand.target_audience ?? ""} onChange={(event) => setBrand({ ...brand, target_audience: event.target.value })} />
        </label>
        <label className="field">
          <span>How should replies sound?</span>
          <textarea value={brand.voice_notes ?? ""} onChange={(event) => setBrand({ ...brand, voice_notes: event.target.value })} />
        </label>
        <label className="field">
          <span>What soft next step is okay to mention?</span>
          <textarea value={brand.call_to_action ?? ""} onChange={(event) => setBrand({ ...brand, call_to_action: event.target.value })} />
        </label>
        <div className="action-row">
          <button className="primary-button" type="submit">Save details</button>
          <button className="secondary-button" type="button" onClick={fillFromWebsite} disabled={!brand.website_url || analyzing}>
            {analyzing ? "Analyzing..." : "Fill from website"}
          </button>
        </div>
      </form>

      <form className="card" onSubmit={analyzeWebsite}>
        <div className="eyebrow">Quick help</div>
        <h2>Fastest way to fill this page</h2>
        <p>Paste your website, click "Analyze website", then edit the results into simple language.</p>
        <button className="secondary-button" type="submit" disabled={!brand.website_url || analyzing}>{analyzing ? "Analyzing..." : "Analyze website"}</button>
        <div className="item-list">
          <div className="list-row">
            <strong>Short summary</strong>
            <p>{brand.summary ?? "No summary yet."}</p>
          </div>
          <div className="list-row">
            <strong>Soft next step</strong>
            <p>{brand.call_to_action ?? "No CTA yet."}</p>
          </div>
          <div className="list-row">
            <strong>Last website scan</strong>
            <p>{brand.last_analyzed_at ?? "Not analyzed yet."}</p>
          </div>
        </div>
      </form>
    </div>
  );
}

import React, { useState } from 'react'

const initialDv360 = {
  advertiser_id: '12345',
  project_id: 'demo-project',
}

const initialCm360 = {
  profile_id: '12345',
}

const initialStudio = {
  user: 'demo@example.com',
}

function App() {
  const [step, setStep] = useState(1)
  const [tenantId, setTenantId] = useState('demo-tenant')
  const [dv360, setDv360] = useState(initialDv360)
  const [cm360, setCm360] = useState(initialCm360)
  const [studio, setStudio] = useState(initialStudio)
  const [feedRowsJson, setFeedRowsJson] = useState(
    JSON.stringify(
      [
        { id: 'row1', segment_id: 'seg_A', headline: 'Buy shoes', image: 'img1.jpg' },
        { id: 'row2', segment_id: 'seg_B', headline: 'Buy hats', image: 'img2.jpg' },
      ],
      null,
      2,
    ),
  )

  const [connectResult, setConnectResult] = useState(null)
  const [selectedCampaignId, setSelectedCampaignId] = useState('')
  const [catalog, setCatalog] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleConnect = async () => {
    setError('')
    let feedRows
    try {
      feedRows = JSON.parse(feedRowsJson)
      if (!Array.isArray(feedRows)) {
        throw new Error('feed_rows must be a JSON array')
      }
    } catch (e) {
      setError('Invalid feed_rows JSON: ' + e.message)
      return
    }

    const payload = {
      tenant_id: tenantId,
      dv360_credentials: dv360,
      cm360_credentials: cm360,
      studio_credentials: studio,
      feed_rows: feedRows,
      linked_campaign_id: null,
    }

    setLoading(true)
    try {
      const resp = await fetch('/adstackr/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const text = await resp.text()
      console.log('status', resp.status)
      console.log('raw response text', text)
      if (!resp.ok) {
        throw new Error('Connect failed: ' + resp.status )
      }
      const data = await resp.json()
      setConnectResult(data)
      if (data.campaigns && data.campaigns.length > 0) {
        setSelectedCampaignId(data.campaigns[0].id)
      }
      setStep(2)
    } catch (e) {
      console.log(e)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectCampaign = async () => {
    if (!selectedCampaignId) return
    setError('')
    setLoading(true)
    try {
      const params = new URLSearchParams({ tenant_id: tenantId, campaign_id: selectedCampaignId })
      const resp = await fetch(`/adstackr/select_campaign?${params.toString()}`, {
        method: 'POST',
      })
      if (!resp.ok) {
        throw new Error('Select campaign failed: ' + resp.status)
      }
      await resp.json()
      setStep(3)

      // Optionally fetch catalog for this tenant
      const catalogResp = await fetch(`/adstackr/catalog?tenant_id=${encodeURIComponent(tenantId)}`)
      if (catalogResp.ok) {
        const cat = await catalogResp.json()
        setCatalog(cat)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '40px auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>AdStackr Connector Demo</h1>
      <p>Golden Path Demo 1.1 / 1.2 – connector + fake Google stack</p>

      {error && (
        <div style={{ color: 'red', marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {step === 1 && (
        <section>
          <h2>Step 1 – Connect Google Marketing Platform</h2>
          <div style={{ marginBottom: 12 }}>
            <label>
              Tenant ID{' '}
              <input
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                style={{ width: 200, marginLeft: 8 }}
              />
            </label>
          </div>

          <h3>DV360 credentials</h3>
          <div style={{ marginBottom: 8 }}>
            <label>
              Advertiser ID{' '}
              <input
                value={dv360.advertiser_id}
                onChange={(e) => setDv360({ ...dv360, advertiser_id: e.target.value })}
                style={{ width: 200, marginLeft: 8 }}
              />
            </label>
          </div>
          <div style={{ marginBottom: 8 }}>
            <label>
              Project ID{' '}
              <input
                value={dv360.project_id}
                onChange={(e) => setDv360({ ...dv360, project_id: e.target.value })}
                style={{ width: 200, marginLeft: 8 }}
              />
            </label>
          </div>

          <h3>CM360 credentials</h3>
          <div style={{ marginBottom: 8 }}>
            <label>
              Profile ID{' '}
              <input
                value={cm360.profile_id}
                onChange={(e) => setCm360({ ...cm360, profile_id: e.target.value })}
                style={{ width: 200, marginLeft: 8 }}
              />
            </label>
          </div>

          <h3>Studio credentials</h3>
          <div style={{ marginBottom: 8 }}>
            <label>
              User email{' '}
              <input
                value={studio.user}
                onChange={(e) => setStudio({ ...studio, user: e.target.value })}
                style={{ width: 260, marginLeft: 8 }}
              />
            </label>
          </div>

          <h3>Feed rows (JSON)</h3>
          <p style={{ fontSize: 12, color: '#555' }}>
            Paste or edit a JSON array of feed rows (each with id, segment_id, and fields like headline, image).
          </p>
          <textarea
            value={feedRowsJson}
            onChange={(e) => setFeedRowsJson(e.target.value)}
            rows={8}
            style={{ width: '100%', fontFamily: 'monospace', fontSize: 12 }}
          />

          <button onClick={handleConnect} disabled={loading} style={{ marginTop: 16 }}>
            {loading ? 'Connecting…' : 'Test & Connect'}
          </button>
        </section>
      )}

      {step === 2 && connectResult && (
        <section>
          <h2>Step 2 – Choose campaign</h2>
          <p>
            Tenant <code>{connectResult.tenant_id}</code>
          </p>

          {connectResult.campaigns && connectResult.campaigns.length > 0 ? (
            <>
              <table
                style={{ borderCollapse: 'collapse', width: '100%', marginTop: 12, marginBottom: 12 }}
              >
                <thead>
                  <tr>
                    <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>ID</th>
                    <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>Name</th>
                    <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>Select</th>
                  </tr>
                </thead>
                <tbody>
                  {connectResult.campaigns.map((c) => (
                    <tr key={c.id}>
                      <td style={{ borderBottom: '1px solid #eee', padding: 4 }}>
                        <code>{c.id}</code>
                      </td>
                      <td style={{ borderBottom: '1px solid #eee', padding: 4 }}>{c.name}</td>
                      <td style={{ borderBottom: '1px solid #eee', padding: 4 }}>
                        <input
                          type="radio"
                          name="campaign"
                          checked={selectedCampaignId === c.id}
                          onChange={() => setSelectedCampaignId(c.id)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <button onClick={handleSelectCampaign} disabled={loading || !selectedCampaignId}>
                {loading ? 'Saving…' : 'Save & Continue'}
              </button>
            </>
          ) : (
            <p>No campaigns returned from Fake Google.</p>
          )}
        </section>
      )}

      {step === 3 && (
        <section>
          <h2>Step 3 – Connected</h2>
          <p>
            Tenant <code>{tenantId}</code> is connected.
          </p>
          <p>
            Selected campaign: <code>{selectedCampaignId}</code>
          </p>

          {catalog && (
            <div style={{ marginTop: 16 }}>
              <h3>Catalog snapshot</h3>
              <pre style={{ background: '#f6f6f6', padding: 12, fontSize: 12 }}>
                {JSON.stringify(catalog, null, 2)}
              </pre>
            </div>
          )}

          <button onClick={() => setStep(1)} style={{ marginTop: 16 }}>
            Start over
          </button>
        </section>
      )}
    </div>
  )
}

export default App


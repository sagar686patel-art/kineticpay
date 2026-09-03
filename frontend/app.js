const API_BASE = "http://127.0.0.1:8000/api";
let cashflowChart = null;

function showTab(tab) {
  const loginForm = document.getElementById("form-login");
  const regForm = document.getElementById("form-register");
  const tabL = document.getElementById("tab-login");
  const tabR = document.getElementById("tab-register");

  if (!loginForm) return;

  if (tab === "login") {
    loginForm.classList.remove("hidden");
    regForm.classList.add("hidden");
    tabL.classList.add("bg-emerald-500", "text-slate-900");
    tabL.classList.remove("text-slate-300");
    tabR.classList.remove("bg-emerald-500", "text-slate-900");
    tabR.classList.add("text-slate-300");
  } else {
    loginForm.classList.add("hidden");
    regForm.classList.remove("hidden");
    tabR.classList.add("bg-emerald-500", "text-slate-900");
    tabR.classList.remove("text-slate-300");
    tabL.classList.remove("bg-emerald-500", "text-slate-900");
    tabL.classList.add("text-slate-300");
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById("reg-fullname").value,
    platform: document.getElementById("reg-platform").value,
    username: document.getElementById("reg-username").value,
    password: document.getElementById("reg-password").value
  };

  try {
    const res = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    alert("Account created successfully! Please sign in.");
    showTab("login");
  } catch (err) {
    alert(err.message);
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const payload = {
    username: document.getElementById("login-username").value,
    password: document.getElementById("login-password").value
  };

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Invalid credentials");
    const user = await res.json();
    localStorage.setItem("user", JSON.stringify(user));
    window.location.href = "dashboard.html";
  } catch (err) {
    alert(err.message);
  }
}

function logout() {
  localStorage.removeItem("user");
  window.location.href = "index.html";
}

async function initDashboard() {
  const user = JSON.parse(localStorage.getItem("user"));
  if (!user) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("user-greeting").innerText = `Operator: ${user.full_name}`;
  document.getElementById("user-badge").innerText = `Platform: ${user.platform}`;
  await refreshDashboardData(user.id);
}

async function refreshDashboardData(userId) {
  try {
    const res = await fetch(`${API_BASE}/user-stats/${userId}`);
    const data = await res.json();

    document.getElementById("card-buffer").innerText = `₹${data.buffer_balance.toFixed(2)}`;
    document.getElementById("card-loan").innerText = `₹${data.active_loan.toFixed(2)}`;
    document.getElementById("card-credit").innerText = `₹${data.pre_approved_credit.toFixed(2)}`;

    updateChart(data.raw_history, data.smoothed_history);
    renderLedger(data.ledger);
  } catch (err) {
    console.error("Failed to load dashboard data", err);
  }
}

function renderLedger(ledger) {
  const tbody = document.getElementById("ledger-body");
  if (!ledger || ledger.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500 font-sans">No shifts recorded yet. Click 'Seed 7-Day Demo' above.</td></tr>`;
    return;
  }

  tbody.innerHTML = ledger.map(s => {
    const vaultTag = s.vault_diff > 0 
      ? `<span class="text-emerald-400">+₹${s.vault_diff.toFixed(2)} (Skimmed)</span>` 
      : (s.vault_diff < 0 ? `<span class="text-sky-400">-₹${Math.abs(s.vault_diff).toFixed(2)} (Top-up)</span>` : `<span class="text-slate-500">₹0.00</span>`);

    return `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="p-3 text-slate-400">#SH-${s.id}</td>
        <td class="p-3 text-amber-300 font-bold">₹${s.raw.toFixed(2)}</td>
        <td class="p-3">${vaultTag}</td>
        <td class="p-3 text-red-400">₹${s.loan_deducted.toFixed(2)}</td>
        <td class="p-3 text-emerald-400 font-bold text-sm">₹${s.smoothed.toFixed(2)}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px]">SETTLED</span></td>
      </tr>
    `;
  }).join("");
}

function updateChart(raw, smoothed) {
  const ctx = document.getElementById("cashflowChart").getContext("2d");
  const labels = raw.map((_, i) => `Shift ${i + 1}`);

  if (cashflowChart) cashflowChart.destroy();

  cashflowChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.length ? labels : ["No Data"],
      datasets: [
        {
          label: "Raw Volatile Earnings",
          data: raw,
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.05)",
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 4,
          tension: 0.3
        },
        {
          label: "KineticPay Stabilized Disbursal",
          data: smoothed,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.15)",
          fill: true,
          borderWidth: 3,
          pointRadius: 4,
          tension: 0.2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: "#1e293b" }, ticks: { color: "#94a3b8" } },
        x: { grid: { color: "#1e293b" }, ticks: { color: "#94a3b8" } }
      },
      plugins: {
        legend: { labels: { color: "#cbd5e1", font: { weight: "bold" } } }
      }
    }
  });
}

async function triggerShiftSim() {
  const user = JSON.parse(localStorage.getItem("user"));
  const earnings = parseFloat(document.getElementById("sim-earnings").value);
  const hours = parseFloat(document.getElementById("sim-hours").value);
  const trips = parseInt(document.getElementById("sim-trips").value);

  if (![earnings, hours, trips].every(Number.isFinite) || earnings < 0 || hours <= 0 || trips < 0) {
    alert("Enter valid non-negative earnings/trips and active hours greater than zero.");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/simulate-shift`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user.id,
        raw_earnings: earnings,
        active_hours: hours,
        trips: trips
      })
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Unable to process shift");
    await refreshDashboardData(user.id);
  } catch (err) {
    alert("Simulation failed: " + err.message);
  }
}

async function requestMicroAdvance() {
  const user = JSON.parse(localStorage.getItem("user"));
  try {
    const res = await fetch(`${API_BASE}/request-advance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: user.id, requested_amount: 2000.0 })
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Unable to approve advance");
    alert("₹2,000 Micro-Advance approved and disbursed instantly via synthetic escrow!");
    await refreshDashboardData(user.id);
  } catch (err) {
    alert("Advance request failed: " + err.message);
  }
}

async function triggerParametricPayout() {
  const user = JSON.parse(localStorage.getItem("user"));
  try {
    const res = await fetch(`${API_BASE}/parametric-claim/${user.id}`, { method: "POST" });
    if (!res.ok) throw new Error((await res.json()).detail || "Unable to settle weather claim");
    const data = await res.json();
    alert(`🌧️ Heavy Rainfall Triggered!\nParametric Shield activated: ₹${data.payout} deposited directly to your Volatility Vault.`);
    await refreshDashboardData(user.id);
  } catch (err) {
    alert("Insurance trigger failed: " + err.message);
  }
}

async function seedDemoData() {
  const user = JSON.parse(localStorage.getItem("user"));
  if (!user) return alert("Please log in first.");

  const seedBtn = document.getElementById("btn-seed");
  seedBtn.innerText = "⏳ Seeding...";
  seedBtn.disabled = true;

  const demoShifts = [
    { raw_earnings: 1200, active_hours: 8.0, trips: 14 },
    { raw_earnings: 1350, active_hours: 8.5, trips: 16 },
    { raw_earnings: 2350, active_hours: 10.5, trips: 25 },
    { raw_earnings: 2200, active_hours: 10.0, trips: 23 },
    { raw_earnings: 400,  active_hours: 3.5,  trips: 4 },
    { raw_earnings: 1100, active_hours: 7.5,  trips: 12 },
    { raw_earnings: 1600, active_hours: 9.0,  trips: 18 }
  ];

  try {
    for (const shift of demoShifts) {
      const res = await fetch(`${API_BASE}/simulate-shift`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.id,
          raw_earnings: shift.raw_earnings,
          active_hours: shift.active_hours,
          trips: shift.trips
        })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Unable to seed demo shift");
    }
    await refreshDashboardData(user.id);
    seedBtn.innerText = "✓ Seeded!";
    setTimeout(() => {
      seedBtn.innerText = "⚡ Seed 7-Day Demo";
      seedBtn.disabled = false;
    }, 2000);
  } catch (err) {
    alert("Seeding failed: " + err.message);
    seedBtn.innerText = "⚡ Seed 7-Day Demo";
    seedBtn.disabled = false;
  }
}

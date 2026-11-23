/* =========================================================
   PWA：安装提示 + Service Worker + APK 状态
   ========================================================= */
(function () {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const note = $("#appNote");
  const installBtn = $("#installBtn");
  const apkBtn = $("#apkBtn");
  let deferred = null;

  const setNote = (s) => { if (note) note.textContent = s; };

  /* ---- Service Worker ---- */
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch(() => {
        setNote("离线缓存注册失败，其余功能不受影响。");
      });
    });
  }

  /* ---- 安装提示 ---- */
  const standalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.matchMedia("(display-mode: fullscreen)").matches ||
    window.navigator.standalone === true;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    if (installBtn) {
      installBtn.textContent = "安装到桌面";
      installBtn.disabled = false;
    }
    setNote("浏览器已就绪，点左侧按钮即可安装。");
  });

  window.addEventListener("appinstalled", () => {
    deferred = null;
    if (installBtn) { installBtn.textContent = "已安装"; installBtn.disabled = true; }
    setNote("已安装到桌面，下次可直接从图标打开。");
  });

  if (installBtn) {
    if (standalone) {
      installBtn.textContent = "已安装";
      installBtn.disabled = true;
    } else {
      installBtn.textContent = "安装到桌面";
    }
    installBtn.addEventListener("click", async () => {
      if (!deferred) {
        setNote("当前浏览器没给出安装入口：安卓用 Chrome / Edge 打开本页，右上角菜单选「安装」；电脑端则在地址栏右侧点安装图标。");
        return;
      }
      deferred.prompt();
      const res = await deferred.userChoice;
      if (res && res.outcome === "accepted") setNote("正在安装…");
      deferred = null;
    });
  }

  /* ---- APK：存在才放行，避免装成假按钮 ---- */
  if (apkBtn) {
    fetch("apk/battery-hot.apk", { method: "HEAD" })
      .then((r) => {
        if (r.ok) {
          apkBtn.textContent = "下载 APK";
          apkBtn.classList.remove("is-disabled");
          apkBtn.setAttribute("href", "apk/battery-hot.apk");
          apkBtn.setAttribute("download", "battery-hot.apk");
          apkBtn.removeAttribute("aria-disabled");
        } else {
          apkBtn.textContent = "打包中";
        }
      })
      .catch(() => { apkBtn.textContent = "打包中"; });
  }

  if (!standalone && !("serviceWorker" in navigator)) {
    setNote("当前浏览器不支持离线缓存，仍可正常浏览在线内容。");
  }
})();

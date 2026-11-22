// A pretend OBS for the README screenshots: replaces WebSocket and answers obs-websocket v5 requests with demo
// data from demo-data.js, so the real app renders as if connected. Loaded before the app by make.py's demo.html.
(() => {
  const D = window.DEMO;
  localStorage.setItem("obsr.pw", JSON.stringify("demo"));
  localStorage.setItem("obsr.dev", JSON.stringify("cam1"));
  const scenes = ["Main camera", "Wide shot", "Slides", "Speaker + slides", "Break", "Ending"];
  const items = { "Main camera": ["CAM 1", "Lectern mic", "Lower third"], "Wide shot": ["CAM 2", "Lectern mic"], "Slides": ["Slides"] };
  const presets = cam => {
    const list = D.presets[cam]; const order = [], map = {};
    list.forEach(([name, view], i) => { const id = "local:" + (i + 1); order.push({ id }); map[id] = { id, name, thumbnail: true, store: "local", view } });
    return { order, presets: map };
  };
  const devs = [{ device: "cam1", source: "CAM 1", name: "ONVIF PTZ Control" }, { device: "cam2", source: "CAM 2", name: "VISCA over IP PTZ Control" }];
  const audio = ["Mic/Aux", "Desktop Audio", "Lectern mic", "Radio mic"];
  const ptz = (req, data) => {
    const cam = devs.find(d => d.device === data.device);
    if (req === "ptz_list_devices") return { devices: devs };
    if (req === "ptz_get_state") return { state: { connected: true, features: { zoom: true, focus: true, autofocus: true }, focus_af_enabled: true } };
    if (req === "ptz_preset_get_list") return { return: presets(cam.source) };
    if (req === "ptz_preset_get_thumbnail") {
      const p = presets(cam.source).presets[data.id]; return { data: D.thumbs[p.view], mime: "image/jpeg" };
    }
    return {};
  };
  const answer = (t, d) => {
    switch (t) {
      case "GetSceneList": return { scenes: scenes.map((n, i) => ({ sceneName: n, sceneIndex: scenes.length - 1 - i })), currentProgramSceneName: "Main camera", currentPreviewSceneName: "Wide shot" };
      case "GetStudioModeEnabled": return { studioModeEnabled: true };
      case "GetCurrentSceneTransition": return { transitionName: "Fade", transitionDuration: 300 };
      case "GetStreamStatus": return { outputActive: true, outputTimecode: "01:12:45.000", outputSkippedFrames: 3, outputTotalFrames: 108000, outputCongestion: 0 };
      case "GetRecordStatus": return { outputActive: true, outputPaused: false, outputTimecode: "01:12:41.000" };
      case "GetStats": return { cpuUsage: 9.4, activeFps: 25, renderSkippedFrames: 0 };
      case "GetInputList": return { inputs: [...audio.map(n => ({ inputName: n, inputKindCaps: 2, unversionedInputKind: "wasapi_input_capture" })),
        { inputName: "CAM 1", inputKindCaps: 1 }, { inputName: "CAM 2", inputKindCaps: 1 }, { inputName: "Slides", inputKindCaps: 1 }] };
      case "GetSpecialInputs": return { desktop1: "Desktop Audio", mic1: "Mic/Aux" };
      case "GetInputMute": return { inputMuted: d.inputName === "Radio mic" };
      case "GetSceneItemList": return { sceneItems: (items[d.sceneName] || []).map(n => ({ sourceName: n, sceneItemEnabled: true, sourceType: "OBS_SOURCE_TYPE_INPUT" })) };
      case "GetSourceActive": return { videoActive: true, videoShowing: true };
      case "GetSourceFilterList": return { filters: [{ filterKind: "ca.secretlab.obs-ptz.onvif", filterSettings: { pan_speed_max: 1, tilt_speed_max: 1 } }] };
      case "GetPersistentData": return { slotValue: null };
      case "GetSceneCollectionList": return { currentSceneCollectionName: "Demo" };
      case "GetSourceScreenshot": return { imageData: D[d.sourceName] || D["Wide shot"] };
      case "CallVendorRequest":
        if (d.vendorName === "obs-ptz") return { responseData: ptz(d.requestType, d.requestData || {}) };
        if (d.vendorName === "AdvancedSceneSwitcher") return { responseData: { isRunning: false } };
        throw { code: 600, comment: "No vendor" };
    }
    return {};
  };
  class FakeWS {
    constructor() { this.readyState = 0; setTimeout(() => { this.readyState = 1; this.msg({ op: 0, d: { rpcVersion: 1 } }) }, 10) }
    msg(o) { this.onmessage && this.onmessage({ data: JSON.stringify(o) }) }
    send(s) {
      const m = JSON.parse(s);
      if (m.op === 1) { setTimeout(() => { this.msg({ op: 2, d: {} }); this.meters() }, 5); return }
      if (m.op !== 6) return;
      const { requestType: t, requestId, requestData } = m.d;
      let st = { result: true, code: 100 }, data;
      try { data = answer(t, requestData || {}) } catch (e) { st = { result: false, code: e.code || 500, comment: e.comment } }
      setTimeout(() => this.msg({ op: 7, d: { requestType: t, requestId, requestStatus: st, responseData: data } }), 3);
    }
    meters() {  // steady demo sound levels for the meters
      const lvl = { "Mic/Aux": 0.03, "Desktop Audio": 0.01, "Lectern mic": 0.35, "Radio mic": 0 };
      setInterval(() => this.msg({ op: 5, d: { eventType: "InputVolumeMeters", eventData: { inputs: audio.map(n => ({ inputName: n,
        inputLevelsMul: [[lvl[n], lvl[n] * 1.3, lvl[n] * 1.3], [lvl[n] * 0.9, lvl[n] * 1.2, lvl[n] * 1.2]] })) } } }), 50);
    }
    close() {}
  }
  window.WebSocket = FakeWS;
  // headless capture runs on simulated time, so the fps badges would read nonsense: hide them
  document.head.insertAdjacentHTML("beforeend", "<style>.fps{display:none!important}</style>");
  // ?tab=cam opens the Camera tab once the app has loaded
  addEventListener("load", () => setTimeout(() => {
    if (location.search.includes("tab=cam")) document.querySelector('[data-tab="tabCam"]').click();
  }, 300));
})();

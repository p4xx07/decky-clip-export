const manifest = {"name":"Clip Export"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const definePlugin = (fn) => {
    return (...args) => {
        return fn(...args);
    };
};

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(e, t) { if (null == e) return {}; var o, r, i = _objectWithoutPropertiesLoose(e, t); if (Object.getOwnPropertySymbols) { var n = Object.getOwnPropertySymbols(e); for (r = 0; r < n.length; r++) o = n[r], -1 === t.indexOf(o) && {}.propertyIsEnumerable.call(e, o) && (i[o] = e[o]); } return i; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (-1 !== e.indexOf(n)) continue; t[n] = r[n]; } return t; }
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: true, configurable: true, writable: true }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var attr = props.attr,
      size = props.size,
      title = props.title,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function FaFileVideo (props) {
  return GenIcon({"attr":{"viewBox":"0 0 384 512"},"child":[{"tag":"path","attr":{"d":"M384 121.941V128H256V0h6.059c6.365 0 12.47 2.529 16.971 7.029l97.941 97.941A24.005 24.005 0 0 1 384 121.941zM224 136V0H24C10.745 0 0 10.745 0 24v464c0 13.255 10.745 24 24 24h336c13.255 0 24-10.745 24-24V160H248c-13.2 0-24-10.8-24-24zm96 144.016v111.963c0 21.445-25.943 31.998-40.971 16.971L224 353.941V392c0 13.255-10.745 24-24 24H88c-13.255 0-24-10.745-24-24V280c0-13.255 10.745-24 24-24h112c13.255 0 24 10.745 24 24v38.059l55.029-55.013c15.011-15.01 40.971-4.491 40.971 16.97z"},"child":[]}]})(props);
}

const getClips = callable("get_clips");
const getEndpoints = callable("get_endpoints");
const pair = callable("pair");
const removeEndpoint = callable("remove_endpoint");
const startExport = callable("start_export");
const getJob = callable("get_job");
function duration(seconds) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}
function messageOf(error) {
    return error instanceof Error ? error.message : String(error);
}
function Content() {
    const [clips, setClips] = SP_REACT.useState([]);
    const [endpoints, setEndpoints] = SP_REACT.useState([]);
    const [selected, setSelected] = SP_REACT.useState("");
    const [receiverUrl, setReceiverUrl] = SP_REACT.useState("");
    const [pairCode, setPairCode] = SP_REACT.useState("");
    const [jobId, setJobId] = SP_REACT.useState("");
    const [job, setJob] = SP_REACT.useState(null);
    const [busy, setBusy] = SP_REACT.useState(false);
    const [status, setStatus] = SP_REACT.useState("");
    const refresh = async () => {
        try {
            const [found, saved] = await Promise.all([getClips(), getEndpoints()]);
            setClips(found);
            setEndpoints(saved);
            setSelected(current => found.some(clip => clip.id === current) ? current : (found[0]?.id ?? ""));
            setStatus(found.length ? "" : "No saved Steam clips found.");
        }
        catch (error) {
            setStatus(messageOf(error));
        }
    };
    SP_REACT.useEffect(() => { void refresh(); }, []);
    SP_REACT.useEffect(() => {
        if (!jobId)
            return;
        let active = true;
        const poll = async () => {
            try {
                const next = await getJob(jobId);
                if (!active)
                    return;
                setJob(next);
                if (next.state !== "working")
                    setJobId("");
            }
            catch (error) {
                if (active) {
                    setJob({ state: "error", message: messageOf(error) });
                    setJobId("");
                }
            }
        };
        void poll();
        const timer = window.setInterval(() => void poll(), 1000);
        return () => { active = false; window.clearInterval(timer); };
    }, [jobId]);
    const exportTo = async (destination) => {
        if (!selected)
            return;
        setBusy(true);
        setJob(null);
        try {
            setJobId(await startExport(selected, destination));
        }
        catch (error) {
            setJob({ state: "error", message: messageOf(error) });
        }
        finally {
            setBusy(false);
        }
    };
    const pairComputer = async () => {
        setBusy(true);
        try {
            const endpoint = await pair(receiverUrl, pairCode);
            setEndpoints(await getEndpoints());
            setPairCode("");
            setStatus(`Paired with ${endpoint.name}`);
        }
        catch (error) {
            setStatus(messageOf(error));
        }
        finally {
            setBusy(false);
        }
    };
    const forget = async (id) => {
        try {
            await removeEndpoint(id);
            setEndpoints(await getEndpoints());
        }
        catch (error) {
            setStatus(messageOf(error));
        }
    };
    return SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: `Saved clips (${clips.length})`, children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void refresh(), children: "Refresh clips" }) }), clips.slice(0, 50).map(clip => SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => setSelected(clip.id), description: `${clip.date} · ${duration(clip.duration_seconds)}${clip.name ? ` · ${clip.name}` : ""}`, children: [clip.id === selected ? "● " : "", clip.game] }) }, clip.id)), clips.length > 50 && SP_JSX.jsx(DFL.PanelSectionRow, { children: "Showing newest 50 clips." })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Export selected clip", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", disabled: !selected || busy || !!jobId, onClick: () => void exportTo("local"), children: "Save MP4 on Deck" }) }), endpoints.map(endpoint => SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", disabled: !selected || busy || !!jobId, onClick: () => void exportTo(endpoint.id), children: ["Send to ", endpoint.name] }) }, endpoint.id)), job && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { children: [job.state === "error" ? "Error: " : "", job.message] }) }), status && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { children: status }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Pair a computer", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "Receiver URL", value: receiverUrl, onChange: event => setReceiverUrl(event.target.value) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "Six-digit code", value: pairCode, onChange: event => setPairCode(event.target.value) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", disabled: busy || !receiverUrl || !pairCode, onClick: () => void pairComputer(), children: "Pair computer" }) }), endpoints.map(endpoint => SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", description: endpoint.url, onClick: () => void forget(endpoint.id), children: ["Forget ", endpoint.name] }) }, `remove-${endpoint.id}`))] })] });
}

var index = definePlugin(() => ({
    name: "Clip Export",
    titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "Clip Export" }),
    content: SP_JSX.jsx(Content, {}),
    icon: SP_JSX.jsx(FaFileVideo, {}),
}));

export { index as default };
//# sourceMappingURL=index.js.map

import { callable, definePlugin } from "@decky/api";
import { ButtonItem, PanelSection, PanelSectionRow, staticClasses, TextField } from "@decky/ui";
import { useEffect, useState } from "react";
import { FaFileVideo } from "react-icons/fa";

type Clip = {
  id: string;
  app_id: number;
  game: string;
  name: string;
  date: string;
  duration_seconds: number;
};
type Endpoint = { id: string; name: string; url: string };
type Job = { state: "working" | "done" | "error"; message: string };

const getClips = callable<[], Clip[]>("get_clips");
const getEndpoints = callable<[], Endpoint[]>("get_endpoints");
const pair = callable<[url: string, code: string], Endpoint>("pair");
const removeEndpoint = callable<[endpointId: string], boolean>("remove_endpoint");
const startExport = callable<[clipId: string, destination: string], string>("start_export");
const getJob = callable<[jobId: string], Job>("get_job");

function duration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function Content() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [receiverUrl, setReceiverUrl] = useState("");
  const [pairCode, setPairCode] = useState("");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  const refresh = async () => {
    try {
      const [found, saved] = await Promise.all([getClips(), getEndpoints()]);
      setClips(found);
      setEndpoints(saved);
      setSelected(current => found.some(clip => clip.id === current) ? current : (found[0]?.id ?? ""));
      setStatus(found.length ? "" : "No saved Steam clips found.");
    } catch (error) {
      setStatus(messageOf(error));
    }
  };

  useEffect(() => { void refresh(); }, []);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    const poll = async () => {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setJob(next);
        if (next.state !== "working") setJobId("");
      } catch (error) {
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

  const exportTo = async (destination: string) => {
    if (!selected) return;
    setBusy(true);
    setJob(null);
    try {
      setJobId(await startExport(selected, destination));
    } catch (error) {
      setJob({ state: "error", message: messageOf(error) });
    } finally {
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
    } catch (error) {
      setStatus(messageOf(error));
    } finally {
      setBusy(false);
    }
  };

  const forget = async (id: string) => {
    try {
      await removeEndpoint(id);
      setEndpoints(await getEndpoints());
    } catch (error) {
      setStatus(messageOf(error));
    }
  };

  return <>
    <PanelSection title={`Saved clips (${clips.length})`}>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => void refresh()}>Refresh clips</ButtonItem>
      </PanelSectionRow>
      {clips.slice(0, 50).map(clip =>
        <PanelSectionRow key={clip.id}>
          <ButtonItem
            layout="below"
            onClick={() => setSelected(clip.id)}
            description={`${clip.date} · ${duration(clip.duration_seconds)}${clip.name ? ` · ${clip.name}` : ""}`}
          >
            {clip.id === selected ? "● " : ""}{clip.game}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {clips.length > 50 && <PanelSectionRow>Showing newest 50 clips.</PanelSectionRow>}
    </PanelSection>

    <PanelSection title="Export selected clip">
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={!selected || busy || !!jobId} onClick={() => void exportTo("local")}>
          Save MP4 on Deck
        </ButtonItem>
      </PanelSectionRow>
      {endpoints.map(endpoint =>
        <PanelSectionRow key={endpoint.id}>
          <ButtonItem layout="below" disabled={!selected || busy || !!jobId} onClick={() => void exportTo(endpoint.id)}>
            Send to {endpoint.name}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {job && <PanelSectionRow><div>{job.state === "error" ? "Error: " : ""}{job.message}</div></PanelSectionRow>}
      {status && <PanelSectionRow><div>{status}</div></PanelSectionRow>}
    </PanelSection>

    <PanelSection title="Pair a computer">
      <PanelSectionRow><TextField label="Receiver URL" value={receiverUrl} onChange={event => setReceiverUrl(event.target.value)} /></PanelSectionRow>
      <PanelSectionRow><TextField label="Six-digit code" value={pairCode} onChange={event => setPairCode(event.target.value)} /></PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy || !receiverUrl || !pairCode} onClick={() => void pairComputer()}>
          Pair computer
        </ButtonItem>
      </PanelSectionRow>
      {endpoints.map(endpoint =>
        <PanelSectionRow key={`remove-${endpoint.id}`}>
          <ButtonItem layout="below" description={endpoint.url} onClick={() => void forget(endpoint.id)}>
            Forget {endpoint.name}
          </ButtonItem>
        </PanelSectionRow>
      )}
    </PanelSection>
  </>;
}

export default definePlugin(() => ({
  name: "Clip Export",
  titleView: <div className={staticClasses.Title}>Clip Export</div>,
  content: <Content />,
  icon: <FaFileVideo />,
}));

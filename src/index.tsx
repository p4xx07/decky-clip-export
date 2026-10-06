import { definePlugin } from "@decky/api";
import { staticClasses } from "@decky/ui";
import { FaFileVideo } from "react-icons/fa";
import { Content } from "./Content";

export default definePlugin(() => ({
  name: "Clip Export",
  titleView: <div className={staticClasses.Title}>Clip Export</div>,
  content: <Content />,
  icon: <FaFileVideo />,
}));

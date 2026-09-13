import { Config } from "@remotion/cli/config";

Config.setChromiumDisableWebSecurity(true);
Config.setChromiumIgnoreCertificateErrors(true);
Config.setChromiumOpenGlRenderer("angle");

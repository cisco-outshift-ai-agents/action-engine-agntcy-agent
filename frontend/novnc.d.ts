declare module "@novnc/novnc" {
  export default class RFB {
    constructor(
      container: HTMLElement,
      url: string,
      options: {
        credentials: {
          password: string;
        };
      }
    );
    clipViewport: boolean;
    scaleViewport: boolean;
    focusOnClick: boolean;
    viewOnly: boolean;
    addEventListener(
      event: "connect" | "disconnect",
      handler: () => void
    ): void;
    disconnect(): void;
  }
}

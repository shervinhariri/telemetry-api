import React, { PropsWithChildren, useEffect } from "react";

type Props = {
  open: boolean;
  title?: string;
  onClose: () => void;
  width?: number; // px
};

export default function SlideOver({
  open,
  title = "Details",
  onClose,
  width = 520,
  children,
}: PropsWithChildren<Props>) {
  useEffect(() => {
    function onEsc(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [onClose]);

  return (
    <div className={`fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`}>
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={`absolute top-0 right-0 h-full bg-[#121316] w-full sm:w-[${width}px] shadow-2xl
          transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-md px-2 py-1 text-zinc-400 hover:text-white hover:bg-white/5"
            aria-label="Close"
          >✕</button>
        </div>
        <div className="h-[calc(100%-56px)] overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}

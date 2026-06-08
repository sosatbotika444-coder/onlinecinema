import { X } from "lucide-react";
import type { ReactNode } from "react";

import Button from "./Button";

interface ModalProps {
  title: string;
  open: boolean;
  children: ReactNode;
  onClose: () => void;
}

export default function Modal({ title, open, children, onClose }: ModalProps) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-panel">
        <div className="modal-head">
          <h2>{title}</h2>
          <Button variant="ghost" icon={<X size={18} />} aria-label="Закрыть" onClick={onClose} />
        </div>
        {children}
      </div>
    </div>
  );
}

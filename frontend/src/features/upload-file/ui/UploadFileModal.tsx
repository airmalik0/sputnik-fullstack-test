"use client";

import { type FormEvent, useState } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { useUploadFile } from "@/features/upload-file/hooks";

type Props = {
  show: boolean;
  onClose: () => void;
};

export function UploadFileModal({ show, onClose }: Props) {
  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const upload = useUploadFile();

  function reset() {
    setTitle("");
    setSelectedFile(null);
    setValidationError(null);
    upload.reset();
  }

  function handleClose() {
    if (upload.isPending) return; // ignore close while a request is in flight
    reset();
    onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !selectedFile) {
      setValidationError("Укажите название и выберите файл");
      return;
    }

    const form = new FormData();
    form.append("title", title.trim());
    form.append("file", selectedFile);

    setValidationError(null);
    try {
      await upload.mutateAsync(form);
      reset();
      onClose();
    } catch {
      // Error surfaced via `upload.error` below; nothing else to do.
    }
  }

  const errorMessage = validationError ?? (upload.error ? upload.error.message : null);

  return (
    <Modal show={show} onHide={handleClose} centered>
      <Form onSubmit={handleSubmit}>
        <Modal.Header closeButton>
          <Modal.Title>Добавить файл</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {errorMessage ? (
            <Alert variant="danger" className="mb-3">
              {errorMessage}
            </Alert>
          ) : null}
          <Form.Group className="mb-3">
            <Form.Label>Название</Form.Label>
            <Form.Control
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Например, Договор с подрядчиком"
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Файл</Form.Label>
            <Form.Control
              type="file"
              onChange={(event) => {
                const input = event.target as HTMLInputElement;
                setSelectedFile(input.files?.[0] ?? null);
              }}
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={handleClose} disabled={upload.isPending}>
            Отмена
          </Button>
          <Button type="submit" variant="primary" disabled={upload.isPending}>
            {upload.isPending ? "Загрузка..." : "Сохранить"}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

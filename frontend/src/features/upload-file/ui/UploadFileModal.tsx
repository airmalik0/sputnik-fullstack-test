/**
 * Upload-file feature: modal with title + file inputs and submit logic.
 *
 * Features bind UI to a side-effecting domain operation. Here:
 *   - validates inputs,
 *   - calls filesApi.upload,
 *   - reports errors,
 *   - notifies the parent on success so it can refetch its data.
 *
 * Kept under `features/` rather than `entities/file/` because creation
 * is a user flow with its own lifecycle (modal open/close, in-progress
 * spinner, error surface), not just a CRUD operation on the entity.
 */

"use client";

import { type FormEvent, useState } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { filesApi } from "@/entities/file/api";

type Props = {
  show: boolean;
  onClose: () => void;
  onUploaded: () => void;
};

export function UploadFileModal({ show, onClose, onUploaded }: Props) {
  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function reset() {
    setTitle("");
    setSelectedFile(null);
    setError(null);
  }

  function handleClose() {
    if (isSubmitting) return; // ignore close while a request is in flight
    reset();
    onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !selectedFile) {
      setError("Укажите название и выберите файл");
      return;
    }

    const form = new FormData();
    form.append("title", title.trim());
    form.append("file", selectedFile);

    setIsSubmitting(true);
    setError(null);
    try {
      await filesApi.upload(form);
      reset();
      onClose();
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить файл");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal show={show} onHide={handleClose} centered>
      <Form onSubmit={handleSubmit}>
        <Modal.Header closeButton>
          <Modal.Title>Добавить файл</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {error ? (
            <Alert variant="danger" className="mb-3">
              {error}
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
          <Button variant="outline-secondary" onClick={handleClose} disabled={isSubmitting}>
            Отмена
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? "Загрузка..." : "Сохранить"}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

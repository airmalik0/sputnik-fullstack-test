/**
 * Page composition root.
 *
 * The job of `page.tsx` is to wire entities and features together —
 * not to fetch data, format dates, or render rows. After the layered
 * refactor it sits at ~70 lines instead of 367; if a screen grows past
 * that again, the right answer is another feature module.
 */

"use client";

import { useState } from "react";
import { Alert, Button, Card, Col, Container, Row } from "react-bootstrap";

import { useAlerts } from "@/entities/alert/hooks";
import { AlertsTable } from "@/entities/alert/ui/AlertsTable";
import { useFiles } from "@/entities/file/hooks";
import { FilesTable } from "@/entities/file/ui/FilesTable";
import { UploadFileModal } from "@/features/upload-file/ui/UploadFileModal";

export default function Page() {
  const files = useFiles();
  const alerts = useAlerts();
  const [showModal, setShowModal] = useState(false);

  const refreshAll = () => {
    void files.refetch();
    void alerts.refetch();
  };

  // Surface the first non-null error from either fetcher. Two parallel
  // banners would be visual noise; the user only needs one nudge to
  // hit refresh.
  const errorMessage = files.error ?? alerts.error;

  return (
    <Container fluid className="py-4 px-4 bg-light min-vh-100">
      <Row className="justify-content-center">
        <Col xxl={10} xl={11}>
          <Card className="shadow-sm border-0 mb-4">
            <Card.Body className="p-4">
              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                  <h1 className="h3 mb-2">Управление файлами</h1>
                  <p className="text-secondary mb-0">
                    Загрузка файлов, просмотр статусов обработки и ленты алертов.
                  </p>
                </div>
                <div className="d-flex gap-2">
                  <Button variant="outline-secondary" onClick={refreshAll}>
                    Обновить
                  </Button>
                  <Button variant="primary" onClick={() => setShowModal(true)}>
                    Добавить файл
                  </Button>
                </div>
              </div>
            </Card.Body>
          </Card>

          {errorMessage ? (
            <Alert variant="danger" className="shadow-sm">
              {errorMessage}
            </Alert>
          ) : null}

          <FilesTable files={files.data} isLoading={files.isLoading} />
          <AlertsTable alerts={alerts.data} isLoading={alerts.isLoading} />
        </Col>
      </Row>

      <UploadFileModal
        show={showModal}
        onClose={() => setShowModal(false)}
        onUploaded={refreshAll}
      />
    </Container>
  );
}

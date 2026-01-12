import React, { useRef, useState } from "react";
import { Alert, Button, StyleSheet, Text, View, ScrollView } from "react-native";
import { CameraView, CameraType, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import axios from "axios";

// IMPORTANT: must be https in .env
const API = process.env.EXPO_PUBLIC_API_URL ?? "https://medscan-lrd7.onrender.com";

type UploadStartResponse = {
  docId: string;
  status: "queued" | "processing" | "done" | "error";
  pages: Array<{
    id: string;
    uri: string;
    width: number;
    height: number;
    page: number;
    text: string;
  }>;
};

type JobStatusResponse = {
  docId: string;
  status: "queued" | "processing" | "done" | "error";
  result?: UploadStartResponse | null;
  error?: string | null;
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function App() {
  const cameraRef = useRef<CameraView | null>(null);

  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<CameraType>("back");
  const [lastUri, setLastUri] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // We display result as "UploadStartResponse" shape (docId/pages)
  const [result, setResult] = useState<UploadStartResponse | null>(null);

  const toggleFacing = () => setFacing((f) => (f === "back" ? "front" : "back"));

  const snap = async () => {
    try {
      setBusy(true);
      const photo = await cameraRef.current?.takePictureAsync({ quality: 0.8 });
      if (!photo?.uri) return Alert.alert("Camera", "No photo captured");
      setLastUri(photo.uri);
      setResult(null);
      Alert.alert("Captured", "Image ready to upload");
    } catch (e: any) {
      Alert.alert("Camera error", e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  const pickImage = async () => {
    try {
      setBusy(true);
      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.9,
      });
      if (res.canceled) return;

      const uri = res.assets?.[0]?.uri;
      if (!uri) return Alert.alert("Picker", "No image selected");

      setLastUri(uri);
      setResult(null);
      Alert.alert("Selected", "Image ready to upload");
    } catch (e: any) {
      Alert.alert("Picker error", e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  const upload = async () => {
    if (!lastUri) return Alert.alert("Upload", "Take or select an image first.");

    try {
      setBusy(true);
      setResult(null);

      const filename = lastUri.split("/").pop() || "scan.jpg";
      const filetype = filename.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg";

      const form = new FormData();
      form.append("files", { uri: lastUri, name: filename, type: filetype } as any);

      // 1) Start upload (can take time for big images)
      const start = await axios.post<UploadStartResponse>(`${API}/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });

      const docId = start.data.docId;

      // Show immediate placeholder result (pages exist even before OCR finishes)
      setResult(start.data);

      Alert.alert("Uploaded ✅", `docId: ${docId}\nNow processing...`);

      // 2) Poll status (never crashes if result/pages missing)
      const maxAttempts = 60; // 2 minutes max
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        await sleep(2000);

        const statusRes = await axios.get<JobStatusResponse>(`${API}/status/${docId}`, {
          timeout: 30000,
        });

        const job = statusRes.data;

        if (job.status === "done") {
          const safeResult = job.result ?? start.data ?? { docId, status: "done", pages: [] };
          const pagesCount = safeResult.pages?.length ?? 0;

          setResult(safeResult);

          Alert.alert("Done ✅", pagesCount > 0 ? `Pages: ${pagesCount}` : "Done, but pages were empty.");
          return;
        }

        if (job.status === "error") {
          Alert.alert("Processing error ❌", job.error ?? "Unknown error");
          return;
        }
      }

      Alert.alert("Still working…", "Processing is taking longer than expected. Try again in a minute.");
    } catch (e: any) {
      Alert.alert("Upload error", e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!permission) return <Text style={styles.text}>Loading…</Text>;

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Camera permission is needed.</Text>
        <Button title="Grant Camera" onPress={requestPermission} />
        <View style={{ height: 10 }} />
        <Button title="Pick Image Instead" onPress={pickImage} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing={facing} />

      <View style={styles.controls}>
        <Button title="Flip" onPress={toggleFacing} disabled={busy} />
        <Button title="Snap" onPress={snap} disabled={busy} />
        <Button title="Pick Image" onPress={pickImage} disabled={busy} />
        <Button title="Upload" onPress={upload} disabled={busy || !lastUri} />
      </View>

      <ScrollView style={styles.panel} contentContainerStyle={{ paddingBottom: 30 }}>
        <Text style={styles.footer}>
          Selected: {lastUri ? "YES" : "NO"}{"\n"}
          Backend: {API}
        </Text>

        <Text style={styles.h2}>Last result</Text>
        {!result ? (
          <Text style={styles.muted}>No result yet. Upload an image to see docId/pages.</Text>
        ) : (
          <View style={styles.card}>
            <Text style={styles.bold}>docId:</Text>
            <Text selectable>{result.docId}</Text>

            <Text style={[styles.bold, { marginTop: 10 }]}>status:</Text>
            <Text>{result.status}</Text>

            <Text style={[styles.bold, { marginTop: 10 }]}>pages:</Text>
            {(result.pages ?? []).map((p) => (
              <View key={p.id} style={styles.pageRow}>
                <Text style={styles.muted}>{p.id}</Text>
                <Text selectable style={styles.uri}>
                  {p.uri}
                </Text>
                {!!p.text && <Text style={styles.textSmall}>Text: {p.text}</Text>}
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  camera: { flex: 1 },
  controls: { padding: 12, gap: 10 },
  panel: { flex: 1, paddingHorizontal: 12 },
  text: { padding: 12, fontSize: 16 },
  textSmall: { fontSize: 12, marginTop: 4, opacity: 0.9 },
  footer: { paddingVertical: 10, fontSize: 12, opacity: 0.8 },
  h2: { fontSize: 16, fontWeight: "600", marginTop: 6, marginBottom: 6 },
  muted: { opacity: 0.7 },
  card: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10 },
  bold: { fontWeight: "700" },
  pageRow: { marginTop: 8 },
  uri: { fontSize: 12 },
});

import React, { useRef, useState } from "react";
import {
  Alert,
  Button,
  FlatList,
  Platform,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { CameraView, CameraType, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import * as WebBrowser from "expo-web-browser";
import axios from "axios";

const API = "http://192.168.12.203:8000";

type Page = {
  id: string;
  uri: string;
  width?: number;
  height?: number;
  page?: number | null;
  text?: string | null;
};

type UploadRes = {
  docId: string;
  pages: Page[];
  summary?: string | null;
};

export default function App() {
  const cameraRef = useRef<CameraView | null>(null);

  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<CameraType>("back");
  const [lastUri, setLastUri] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [result, setResult] = useState<UploadRes | null>(null);

  const toggleFacing = () => setFacing((f) => (f === "back" ? "front" : "back"));

  const snap = async () => {
    try {
      setBusy(true);
      const photo = await cameraRef.current?.takePictureAsync({ quality: 0.8 });
      if (!photo?.uri) return;

      setLastUri(photo.uri);
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
      if (!uri) return;

      setLastUri(uri);
      Alert.alert("Selected", "Image ready to upload");
    } catch (e: any) {
      Alert.alert("Picker error", e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  const upload = async () => {
    if (!lastUri) {
      Alert.alert("Upload", "Take or select an image first");
      return;
    }

    try {
      setBusy(true);
      setResult(null);

      const form = new FormData();
      form.append("files", {
        uri: lastUri,
        name: "scan.jpg",
        type: "image/jpeg",
      } as any);

      const { data } = await axios.post<UploadRes>(`${API}/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(data);
    } catch (e: any) {
      Alert.alert("Upload error", e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  const clear = () => {
    setLastUri(null);
    setResult(null);
  };

  const openUri = async (uri: string) => {
    // If backend returns a key/path, we *might* need to prefix it later.
    // For now, try opening as-is.
    try {
      if (Platform.OS === "web") {
        window.open(uri, "_blank");
      } else {
        await WebBrowser.openBrowserAsync(uri);
      }
    } catch (e: any) {
      Alert.alert("Open failed", e?.message ?? String(e));
    }
  };

  if (!permission) return <Text style={styles.text}>Loading…</Text>;

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Camera permission is needed</Text>
        <Button title="Grant Camera" onPress={requestPermission} />
        <View style={{ height: 10 }} />
        <Button title="Pick Image Instead" onPress={pickImage} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera */}
      <CameraView ref={cameraRef} style={styles.camera} facing={facing} />

      {/* Controls */}
      <View style={styles.controls}>
        <Button title="Flip" onPress={toggleFacing} disabled={busy} />
        <Button title="Snap" onPress={snap} disabled={busy} />
        <Button title="Pick Image" onPress={pickImage} disabled={busy} />
        <Button title="Upload" onPress={upload} disabled={busy || !lastUri} />
        <Button title="Clear" onPress={clear} disabled={busy} />
      </View>

      {/* Status */}
      <Text style={styles.footer}>
        Selected: {lastUri ? "YES" : "NO"}{"\n"}
        Backend: {API}
      </Text>

      {/* Result Panel */}
      {result && (
        <View style={styles.resultBox}>
          <Text style={styles.resultTitle}>Upload Result</Text>
          <Text style={styles.resultLine}>docId: {result.docId}</Text>
          <Text style={styles.resultLine}>pages: {result.pages?.length ?? 0}</Text>
          {!!result.summary && (
            <Text style={styles.resultLine}>summary: {result.summary}</Text>
          )}

          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Pages</Text>

          <FlatList
            data={result.pages}
            keyExtractor={(p) => p.id}
            renderItem={({ item }) => (
              <View style={styles.pageRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.pageText}>id: {item.id}</Text>
                  <Text style={styles.pageText}>uri: {item.uri}</Text>
                </View>
                <Button title="Open" onPress={() => openUri(item.uri)} />
              </View>
            )}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  camera: { flex: 1 },
  controls: { padding: 12, gap: 10 },
  text: { padding: 12, fontSize: 16 },
  footer: { padding: 12, fontSize: 12, opacity: 0.75 },

  resultBox: {
    padding: 12,
    borderTopWidth: 1,
  },
  resultTitle: { fontSize: 16, fontWeight: "600", marginBottom: 6 },
  resultLine: { fontSize: 13, marginBottom: 4 },
  pageRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 8,
    borderTopWidth: 1,
  },
  pageText: { fontSize: 12, marginBottom: 2 },
});



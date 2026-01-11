import React, { useState } from "react";
import { Button, View, Text, StyleSheet } from "react-native";
import * as Camera from "expo-camera";
import * as MediaLibrary from "expo-media-library";
import axios from "axios";

const API = "http://localhost:8000";

export default function App() {
  const [permission, requestPermission] = Camera.useCameraPermissions();
  const [pages, setPages] = useState<string[]>([]);

  if (!permission) return <Text>Loading</Text>;
  if (!permission.granted) {
    return <Button title="Grant camera" onPress={requestPermission} />;
  }

  const takePicture = async () => {
    const photo = await Camera.takePictureAsync({ quality: 0.8, base64: true });
    setPages((p) => [...p, photo.uri]);
  };

  const savePdf = async () => {
    const form = new FormData();
    pages.forEach((uri, i) => {
      form.append("files", { uri, name: `p${i}.jpg`, type: "image/jpeg" } as any);
    });
    const { data } = await axios.post(`${API}/upload`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    alert(`Uploaded doc ${data.docId} with ${data.pages.length} pages`);
  };

  return (
    <View style={styles.container}>
      <Camera style={styles.camera} type={Camera.CameraType.back} />
      <Button title="Snap" onPress={takePicture} />
      <Button title="Finish & Upload" onPress={savePdf} disabled={pages.length === 0} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  camera: { flex: 1 },
});

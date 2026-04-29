package com.gyro.udp;

import android.app.Activity;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.graphics.Color;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity implements SensorEventListener {

    private SensorManager sensorManager;
    private Sensor orientationSensor;
    private DatagramSocket udpSocket;
    
    private boolean isStreaming = false;
    private InetAddress targetAddress;
    private int targetPort = 8002;

    private TextView statusText;
    private EditText ipInput;
    private Button toggleButton;
    
    private ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(Bundle savedInstanceState);
        
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(50, 50, 50, 50);

        ipInput = new EditText(this);
        ipInput.setHint("Enter Target IP Address (e.g. 192.168.x.x)");
        ipInput.setTextSize(20);
        layout.addView(ipInput);

        toggleButton = new Button(this);
        toggleButton.setText("Connect & Start Gyro");
        toggleButton.setTextSize(20);
        layout.addView(toggleButton);

        statusText = new TextView(this);
        statusText.setText("Disconnected");
        statusText.setTextSize(20);
        statusText.setPadding(0, 50, 0, 0);
        layout.addView(statusText);

        setContentView(layout);

        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        orientationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ORIENTATION);

        try {
            udpSocket = new DatagramSocket();
        } catch (Exception e) {
            e.printStackTrace();
        }

        toggleButton.setOnClickListener(v -> {
            if (!isStreaming) {
                try {
                    String ip = ipInput.getText().toString().trim();
                    if(ip.isEmpty()) {
                        statusText.setText("Please enter an IP address");
                        return;
                    }
                    targetAddress = InetAddress.getByName(ip);
                    isStreaming = true;
                    toggleButton.setText("Stop Streaming");
                    statusText.setText("Streaming to " + ip + ":" + targetPort);
                    statusText.setTextColor(Color.GREEN);
                    
                    sensorManager.registerListener(this, orientationSensor, SensorManager.SENSOR_DELAY_FASTEST);
                } catch (Exception e) {
                    statusText.setText("Invalid IP Address");
                    statusText.setTextColor(Color.RED);
                }
            } else {
                isStreaming = false;
                toggleButton.setText("Connect & Start Gyro");
                statusText.setText("Disconnected");
                statusText.setTextColor(Color.BLACK);
                sensorManager.unregisterListener(this);
            }
        });
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!isStreaming || udpSocket == null || targetAddress == null) return;
        
        float alpha = event.values[0];
        float beta = event.values[1];
        float gamma = event.values[2];
        long timestamp = System.currentTimeMillis();

        executor.execute(() -> {
            try {
                // 8 bytes for long timestamp, 12 bytes for 3 floats = 20 bytes
                ByteBuffer buffer = ByteBuffer.allocate(20);
                buffer.order(ByteOrder.LITTLE_ENDIAN); // Match Python's '<'
                buffer.putLong(timestamp);
                buffer.putFloat(alpha);
                buffer.putFloat(beta);
                buffer.putFloat(gamma);

                byte[] data = buffer.array();
                DatagramPacket packet = new DatagramPacket(data, data.length, targetAddress, targetPort);
                udpSocket.send(packet);
            } catch (Exception e) {
                // Ignore drop exceptions
            }
        });
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) { }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (udpSocket != null) udpSocket.close();
        sensorManager.unregisterListener(this);
        executor.shutdown();
    }
}

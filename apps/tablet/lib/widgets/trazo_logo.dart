import 'package:flutter/material.dart';

import '../theme.dart';

/// Logo de Reminia: azulejo salvia redondeado con anillos concéntricos blancos
/// (evocan la memoria, los recuerdos que vuelven) y un punto coral en el centro.
/// Dibujado con CustomPainter (sin dependencias ni assets).
class TrazoLogo extends StatelessWidget {
  final double size;

  const TrazoLogo({super.key, this.size = 96});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _TrazoLogoPainter()),
    );
  }
}

class _TrazoLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Azulejo salvia redondeado.
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, w, h),
      Radius.circular(w * 0.28),
    );
    final tilePaint = Paint()..color = TrazoColors.sage;
    canvas.drawRRect(rect, tilePaint);

    // Anillos concéntricos blancos (coordenadas relativas al lienzo 40x40).
    final center = Offset(w / 2, h / 2);
    final ringPaint = Paint()
      ..color = TrazoColors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.065
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, w * (12.5 / 40), ringPaint);
    canvas.drawCircle(center, w * (7 / 40), ringPaint);

    // Punto coral en el centro.
    final dotPaint = Paint()..color = TrazoColors.coral;
    canvas.drawCircle(center, w * 0.06, dotPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

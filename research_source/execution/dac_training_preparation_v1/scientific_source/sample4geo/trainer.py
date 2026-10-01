import time

import torch

from tqdm import tqdm

from .utils import AverageMeter

from torch.cuda.amp import autocast

import torch.nn.functional as F

from sample4geo.loss.cal_loss import cal_kl_loss, cal_loss, cal_triplet_loss

import torch.nn as nn

def train(train_config, model, dataloader, loss_functions, optimizer, epoch, train_steps_per, tensorboard=None,
          scheduler=None, scaler=None):
    # set model train mode
    model.train()

    losses = AverageMeter()

    # wait before starting progress bar
    time.sleep(0.1)

    # Zero gradients for first step
    optimizer.zero_grad(set_to_none=True)

    step = 1

    if train_config.verbose:
        bar = tqdm(dataloader, total=len(dataloader))
    else:
        bar = dataloader

    criterion = nn.CrossEntropyLoss()

    # for loop over one epoch
    for query, reference, ids, labels in bar:

        if scaler:
            with (autocast()):  # -- 使用混合精度
                # data (batches) to device   
                query = query.to(train_config.device)
                reference = reference.to(train_config.device)
                labels = labels.to(train_config.device)

                # Forward pass
                if train_config.handcraft_model is not True:
                    features1, features2 = model(query, reference)
                else:
                    output1, output2 = model(query, reference)
                    features1, features2 = output1[-2], output2[-2]  # -- for contrastive
                    features_tri_1, features_tri_2 = output1[2], output2[2]  # -- for triplet
                    features_cls_1, features_cls_2 = output1[1], output2[1]  # -- for classifier
                    features_fine_1, features_fine_2 = output1[-1], output2[-1]  # -- for fine-grained
                    features_dsa_1, features_dsa_2 = output1[0], output2[0]  # -- for DSA loss

                if torch.cuda.device_count() > 1 and len(train_config.gpu_ids) > 1:
                    loss = loss_functions["infoNCE"](features1, features2, model.module.logit_scale.exp())
                else:
                    # 1. infoNCE
                    loss = loss_functions["infoNCE"](features1, features2, model.logit_scale.exp())

                    # 2. Classification
                    loss_cls = cal_loss(features_cls_1, labels, criterion) + cal_loss(features_cls_2, labels, criterion)


                    # 3. Domian Space Alignment Loss
                    loss_DSA = loss_functions["DSA_loss"](features_dsa_1, features_dsa_2,
                                                          model.logit_scale_blocks.exp())


                lossall = train_config.weight_infonce * loss + train_config.weight_cls * loss_cls + train_config.weight_dsa * loss_DSA

                # lossall = 1.0 * loss + 0.0 * loss_cls + 0.0 * loss_DSA

                losses.update(lossall.item())

            # scaler.scale(loss).backward()  # -- 混合精度好像是这样用的
            scaler.scale(lossall).backward()  # -- 这里才是反向传播，上面就是记录一下

            # Gradient clipping
            if train_config.clip_grad:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_value_(model.parameters(), train_config.clip_grad)

                # Update model parameters (weights)
            scaler.step(optimizer)
            scaler.update()

            # Zero gradients for next step
            optimizer.zero_grad()

            # Scheduler
            if train_config.scheduler == "polynomial" or train_config.scheduler == "cosine" or train_config.scheduler == "constant":
                scheduler.step()

        else:

            # data (batches) to device   
            query = query.to(train_config.device)
            reference = reference.to(train_config.device)

            # Forward pass
            features1, features2 = model(query, reference)
            if torch.cuda.device_count() > 1 and len(train_config.gpu_ids) > 1:
                loss = loss_functions["infoNCE"](features1, features2, model.module.logit_scale.exp())
            else:
                loss = loss_functions["infoNCE"](features1, features2, model.logit_scale.exp())
            losses.update(loss.item())

            # Calculate gradient using backward pass
            loss.backward()

            # Gradient clipping 
            if train_config.clip_grad:
                torch.nn.utils.clip_grad_value_(model.parameters(), train_config.clip_grad)

                # Update model parameters (weights)
            optimizer.step()
            # Zero gradients for next step
            optimizer.zero_grad()

            # Scheduler
            if train_config.scheduler == "polynomial" or train_config.scheduler == "cosine" or train_config.scheduler == "constant":
                scheduler.step()

        if train_config.verbose:
            # tst = model.logit_scale
            monitor = {
                "loss": "{:.4f}".format(loss.item()),
                "loss_cls": "{:.4f}".format(train_config.weight_cls * loss_cls.item()),
                "loss_dsa": "{:.4f}".format(train_config.weight_dsa * loss_DSA.item()),
                "loss_avg": "{:.4f}".format(losses.avg),
                "lr": "{:.6f}".format(optimizer.param_groups[0]['lr'])}

            bar.set_postfix(ordered_dict=monitor)

            if tensorboard is not None:
                steps = step + (epoch - 1) * train_steps_per
                tensorboard.add_scalar("Loss", lossall.item(), steps)
                tensorboard.add_scalar("Loss_Avg", losses.avg, steps)
                tensorboard.add_scalar("Learning_Rate", optimizer.param_groups[0]['lr'], steps)
                tensorboard.add_scalar("Learning_Rate_Temp", optimizer.param_groups[-1]['lr'], steps)
                tensorboard.add_scalar("Temperature", model.logit_scale.detach().cpu().numpy(), steps)

        step += 1

    if train_config.verbose:
        bar.close()

    return losses.avg
